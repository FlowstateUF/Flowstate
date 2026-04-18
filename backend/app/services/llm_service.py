import json, random, re
from openai import OpenAI
from .question_prompts import (
    MC_BASE_PROMPT,
    QUESTION_TYPES,
    FLASHCARD_PROMPT,
    SUMMARY_PROMPT,
    PRETEST_PROMPT,
    TEXTBOOK_CHAT_PROMPT,
    MC_MIXED_PROMPT,
)


# Turns buffered paragraph lines into one answer block.
def flush_paragraph_block(paragraph_lines: list[str], blocks: list[dict]):
    if not paragraph_lines:
        return

    text = " ".join(line.strip() for line in paragraph_lines if line.strip()).strip()
    paragraph_lines.clear()
    if text:
        blocks.append({
            "type": "paragraph",
            "text": text,
            "citations": [],
        })


# Sets the target mix of quiz question types for each difficulty.
def build_quiz_type_distribution(difficulty: str, num_questions: int) -> str:
    difficulty_key = (difficulty or "easy").strip().lower()
    total_questions = max(1, int(num_questions or 1))

    ratio_map = {
        "easy": [("recall", 0.7), ("understand", 0.3)],
        "medium": [("recall", 0.2), ("understand", 0.5), ("apply", 0.3)],
        "hard": [("understand", 0.2), ("apply", 0.4), ("analyze", 0.4)],
    }
    ratios = ratio_map.get(difficulty_key, ratio_map["easy"])

    counts = {question_type: int(total_questions * ratio) for question_type, ratio in ratios}
    allocated = sum(counts.values())
    remainders = sorted(
        [
            ((total_questions * ratio) - counts[question_type], question_type)
            for question_type, ratio in ratios
        ],
        reverse=True,
    )

    for _, question_type in remainders[: max(0, total_questions - allocated)]:
        counts[question_type] += 1

    return "\n".join(
        f"- {count} {question_type}" for question_type, count in counts.items() if count > 0
    )


# Handles prompt building and response cleanup for Flo and study tools.
class LLMService:
    
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.ai.it.ufl.edu"
        )
        self.model = "gpt-oss-20b"

    # Used to construct the LLM prompt with the provided context and question type
    def build_question_prompt(self, context, question_type, temp):
        
        # Check if question type exists
        if question_type not in QUESTION_TYPES:
            raise ValueError(f"Unknown question type: {question_type}")
        
        # Fill in the template
        return MC_BASE_PROMPT.format(
            context=context,
            question_instructions=QUESTION_TYPES[question_type]
        )
    
    # Parses the JSON output provided from the LLM
    def parse_question_response(self, response_text):
        
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            raise ValueError("LLM didn't return valid JSON")
        
        # Check if LLM said insufficient context
        if "error" in data:
            raise ValueError(f"LLM error: {data['error']}")
        
        # Make sure all required fields are there
        required = ['question', 'choices', 'correct_answer', 'explanation', 'citation']
        missing = [f for f in required if f not in data]
        if missing:
            raise ValueError(f"Response missing: {missing}")
        
        return data
        
    # Parses JSON responses for flashcards, summaries, and chat output.
    def parse_json_response(self, response_text: str):
        if not response_text or not response_text.strip():
            raise ValueError("LLM returned empty text")

        txt = response_text.strip()

        txt = re.sub(r"^```(?:json)?\s*", "", txt)
        txt = re.sub(r"\s*```$", "", txt).strip()

        try:
            data = json.loads(txt)
        except json.JSONDecodeError:
            m = re.search(r"(\{.*\}|\[.*\])", txt, re.DOTALL)
            if not m:
                raise ValueError(f"LLM didn't return valid JSON. Got: {txt[:200]!r}")
            data = json.loads(m.group(1))

        if isinstance(data, dict) and "error" in data:
            raise ValueError(f"LLM error: {data['error']}")
        return data
    
    def get_response_text(self, response) -> str:
        text = getattr(response, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        chunks = []
        output = getattr(response, "output", None) or []
        for item in output:
            content = getattr(item, "content", None) or []
            for part in content:
                part_type = getattr(part, "type", None)
                part_text = getattr(part, "text", None)
                if part_type in ("output_text", "text") and isinstance(part_text, str):
                    chunks.append(part_text)

        joined = "\n".join(chunks).strip()
        return joined

    def remove_citations_from_answer(self, answer: str, citations: list[str]) -> str:
        cleaned = (answer or "").strip()
        if not cleaned:
            return cleaned

        cleaned = re.sub(r"\s*\((?:see\s+)?pages?\s+[ivxlcdm0-9\-–,\s]+(?:\s*(?:and|or)\s+pages?\s+[ivxlcdm0-9\-–,\s]+)?\)\s*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(?:see|on|from)\s+pages?\s+[ivxlcdm0-9\-–,\s]+(?=[.,;:]|\s|$)", " ", cleaned, flags=re.IGNORECASE)

        for citation in citations or []:
            escaped = re.escape((citation or "").strip())
            if not escaped:
                continue
            cleaned = re.sub(rf"\s*\({escaped}\)\s*", " ", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(rf"\s*{escaped}\s*", " ", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip()

    # Cleans citation strings and keeps the first copy.
    def normalize_citations(self, citations: list[str]) -> list[str]:
        normalized = []
        seen = set()

        for citation in citations or []:
            if not isinstance(citation, str):
                continue
            cleaned = citation.strip()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)

        return normalized

    # Pulls any block-level citations out before we normalize the answer.
    def collect_block_citations(self, raw_blocks) -> list[str]:
        citations = []

        if not isinstance(raw_blocks, list):
            return citations

        for block in raw_blocks:
            if not isinstance(block, dict):
                continue
            citations.extend(block.get("citations") or [])

        return citations

    # Rebuilds the plain answer text from the structured blocks.
    def compose_answer_from_blocks(self, blocks: list[dict]) -> str:
        lines = []

        for block in blocks or []:
            block_type = block.get("type")
            text = (block.get("text") or "").strip()
            if not text:
                continue

            if block_type == "heading":
                lines.append(f"## {text}")
            elif block_type == "bullet":
                lines.append(f"- {text}")
            else:
                lines.append(text)

        return "\n".join(lines).strip()

    # Spreads fallback citations across the answer blocks when needed.
    def spread_citations_across_blocks(self, blocks: list[dict], citations: list[str]) -> list[dict]:
        if not blocks or not citations:
            return blocks

        content_indexes = [
            index for index, block in enumerate(blocks)
            if block.get("type") != "heading"
        ]
        if not content_indexes:
            return blocks

        if len(content_indexes) == 1:
            blocks[content_indexes[0]]["citations"] = citations[:]
            return blocks

        citation_total = len(citations)
        content_total = len(content_indexes)

        for order, block_index in enumerate(content_indexes):
            start = round((order * citation_total) / content_total)
            end = round(((order + 1) * citation_total) / content_total)
            blocks[block_index]["citations"] = citations[start:end]

        return blocks

    # Turns a plain answer into blocks if the model skips the structured format.
    def build_fallback_answer_blocks(self, answer: str, citations: list[str]) -> list[dict]:
        lines = (answer or "").splitlines()
        blocks = []
        paragraph_lines = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                flush_paragraph_block(paragraph_lines, blocks)
                continue

            if re.match(r"^\s{0,3}#{1,3}\s+", line):
                flush_paragraph_block(paragraph_lines, blocks)
                blocks.append({
                    "type": "heading",
                    "text": re.sub(r"^\s{0,3}#{1,3}\s+", "", line).strip(),
                    "citations": [],
                })
                continue

            if re.match(r"^\s*[-*]\s+", line):
                flush_paragraph_block(paragraph_lines, blocks)
                blocks.append({
                    "type": "bullet",
                    "text": re.sub(r"^\s*[-*]\s+", "", line).strip(),
                    "citations": [],
                })
                continue

            paragraph_lines.append(line)

        flush_paragraph_block(paragraph_lines, blocks)

        if not blocks and (answer or "").strip():
            blocks = [{
                "type": "paragraph",
                "text": (answer or "").strip(),
                "citations": [],
            }]

        return self.spread_citations_across_blocks(blocks, citations)

    # Normalizes the model's answer blocks so the UI can trust them.
    def normalize_answer_blocks(self, raw_blocks, answer: str, citations: list[str]) -> list[dict]:
        normalized_blocks = []
        allowed_types = {"paragraph", "bullet", "heading"}

        if isinstance(raw_blocks, list):
            for raw_block in raw_blocks:
                if not isinstance(raw_block, dict):
                    continue

                text = self.remove_citations_from_answer(
                    (raw_block.get("text") or "").strip(),
                    citations,
                )
                if not text:
                    continue

                block_type = raw_block.get("type")
                if block_type not in allowed_types:
                    block_type = "paragraph"

                block_citations = [
                    citation
                    for citation in self.normalize_citations(raw_block.get("citations") or [])
                    if citation in citations
                ][:2]

                normalized_blocks.append({
                    "type": block_type,
                    "text": text,
                    "citations": block_citations,
                })

        return normalized_blocks or self.build_fallback_answer_blocks(answer, citations)

    def question_has_external_reference(self, question_text: str) -> bool:
        text = (question_text or "").strip().lower()
        if not text:
            return True

        disallowed_patterns = [
            r"\bexample above\b",
            r"\bexample below\b",
            r"\babove example\b",
            r"\bbelow example\b",
            r"\bfigure\b",
            r"\bdiagram\b",
            r"\bgraph\b",
            r"\bchart\b",
            r"\btable\b",
            r"\bimage\b",
            r"\bpicture\b",
            r"\billustration\b",
            r"\bshown above\b",
            r"\bshown below\b",
            r"\bas shown\b",
            r"\bpictured\b",
            r"\bdisplayed\b",
            r"\bcode snippet\b",
            r"\bsnippet above\b",
            r"\bsee above\b",
            r"\bsee below\b",
        ]
        return any(re.search(pattern, text) for pattern in disallowed_patterns)

    def validate_pretest_question(self, question: dict, index: int):
        required = ["type", "question", "choices", "correct_answer", "explanation", "citation"]
        answer_labels = {"A", "B", "C", "D"}
        valid_types = {"recall", "understand", "apply", "analyze"}

        missing = [field for field in required if field not in question]
        if missing:
            raise ValueError(f"Question {index} missing fields: {missing}")

        if question["type"] not in valid_types:
            raise ValueError(f"Question {index} has invalid type: {question['type']}")

        if not isinstance(question["choices"], dict) or set(question["choices"].keys()) != answer_labels:
            raise ValueError(f"Question {index} must include choices A, B, C, D")

        if (question["correct_answer"] or "").strip().upper() not in answer_labels:
            raise ValueError(f"Question {index} has invalid correct_answer: {question['correct_answer']}")

        prompt_text = (question.get("question") or "").strip()
        if len(prompt_text) < 12:
            raise ValueError(f"Question {index} is too short to be self-contained")

        if self.question_has_external_reference(prompt_text):
            raise ValueError(
                f"Question {index} is not self-contained and appears to reference hidden external material: {prompt_text}"
            )

    def validate_pretest_questions(self, questions: list[dict], expected_count: int):
        if len(questions) != expected_count:
            raise ValueError(f"Expected {expected_count} questions, got {len(questions)}")

        for i, question in enumerate(questions):
            self.validate_pretest_question(question, i)

    # Generates a question using the given context and question type
    def generate_question(self, context, question_type, temp):

        # Build the prompt
        prompt = self.build_question_prompt(context, question_type, temp)
        
        # Call the LLM
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )
        
        # Parse and return the result
        return self.parse_question_response(response.output_text)

    def generate_flashcards(self, context, num_cards=10, temp=0.3):
        prompt = FLASHCARD_PROMPT.format(
            context=context,
            num_cards=num_cards
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )

        data = self.parse_json_response(response.output_text)

        if "flashcards" not in data or not isinstance(data["flashcards"], list):
            raise ValueError("Response missing 'flashcards' list")

        return data

    def generate_summary(self, context, temp=0.3):
        prompt = SUMMARY_PROMPT.format(context=context)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )

        raw_text = self.get_response_text(response)
        data = self.parse_json_response(raw_text)

        if "summary" not in data or not isinstance(data["summary"], dict):
            raise ValueError("Response missing 'summary' object")

        return data
    
    def generate_pretest(self, chapter_title, context, temp=0.3):
        
        bloom_distribution_str = (
            "- 5 Recall (Bloom's Level 1)\n"
            "- 3 Understand (Bloom's Level 2)\n"
            "- 2 Apply (Bloom's Level 3)\n"
            "- 2 Analyze (Bloom's Level 4)"
        )

        # Should match distribution above (if ever changed)
        PRETEST_Q_COUNT = 12

        prompt = PRETEST_PROMPT.format(
            chapter_title=chapter_title,
            question_count=PRETEST_Q_COUNT,
            bloom_distribution=bloom_distribution_str,
            context=context
        )

        last_error = None

        for attempt in range(2):
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=temp
            )

            data = self.parse_json_response(response.output_text)

            if "questions" not in data or not isinstance(data["questions"], list):
                raise ValueError("Response missing 'questions' list")

            try:
                self.validate_pretest_questions(data["questions"], PRETEST_Q_COUNT)
                return self.shuffle_questions_choices(data["questions"])
            except ValueError as exc:
                last_error = exc
                print(f"[pretest] validation failed on attempt {attempt + 1}: {exc}")

        raise last_error or ValueError("Pretest generation failed validation")

    def shuffle_question_choices(self, question: dict) -> dict:
        choices = question.get("choices") or {}
        correct_answer = (question.get("correct_answer") or "").strip().upper()
        answer_labels = ["A", "B", "C", "D"]
        ordered_choices = [(label, choices[label]) for label in answer_labels]

        shuffled_choices = ordered_choices[:]
        if len({text for _, text in ordered_choices}) > 1:
            for _ in range(5):
                random.shuffle(shuffled_choices)
                if shuffled_choices != ordered_choices:
                    break

        remapped_choices = {}
        new_correct_answer = correct_answer

        for new_label, (old_label, choice_text) in zip(answer_labels, shuffled_choices):
            remapped_choices[new_label] = choice_text
            if old_label == correct_answer:
                new_correct_answer = new_label

        return {
            **question,
            "choices": remapped_choices,
            "correct_answer": new_correct_answer,
        }

    def shuffle_questions_choices(self, questions: list[dict]) -> list[dict]:
        return [self.shuffle_question_choices(question) for question in questions]
    
    def generate_quiz(self, context, difficulty="easy", num_questions=10, temp=0.3):
        type_distribution = build_quiz_type_distribution(difficulty, num_questions)
        prompt = MC_MIXED_PROMPT.format(
            context=context,
            num_questions=num_questions,
            difficulty=difficulty.upper(),
            type_distribution=type_distribution,
        )

        raw = self.generate_raw(prompt, temperature=temp)

        try:
            result = self.parse_json_response(raw)
        except Exception:
            return {"questions": []}

        questions = result.get("questions", [])
        if not isinstance(questions, list):
            return {"questions": []}

        cleaned_questions = []
        seen_questions = set()
        valid_types = {"recall", "understand", "apply", "analyze"}

        for q in questions:
            if not isinstance(q, dict):
                continue

            question_text = (q.get("question") or "").strip()
            choices = q.get("choices")
            correct_answer = (q.get("correct_answer") or "").strip().upper()
            explanation = (q.get("explanation") or "").strip()
            citation = (q.get("citation") or "").strip()
            question_type = (q.get("type") or "").strip().lower()

            if not question_text or not isinstance(choices, dict):
                continue

            if set(choices.keys()) != {"A", "B", "C", "D"}:
                continue

            if correct_answer not in {"A", "B", "C", "D"}:
                continue

            normalized_question = re.sub(r"\s+", " ", question_text.lower())
            if normalized_question in seen_questions:
                continue
            seen_questions.add(normalized_question)

            normalized_choices = {}
            choice_values = []

            invalid_choice = False
            for label in ["A", "B", "C", "D"]:
                value = choices.get(label)
                if not isinstance(value, str) or not value.strip():
                    invalid_choice = True
                    break
                cleaned_value = value.strip()
                normalized_choices[label] = cleaned_value
                choice_values.append(cleaned_value.lower())

            if invalid_choice:
                continue

            if len(set(choice_values)) < 4:
                continue

            if question_type not in valid_types:
                if difficulty == "easy":
                    question_type = "recall"
                elif difficulty == "medium":
                    question_type = "understand"
                else:
                    question_type = "analyze"

            cleaned_questions.append({
                "type": question_type,
                "question": question_text,
                "choices": normalized_choices,
                "correct_answer": correct_answer,
                "explanation": explanation,
                "citation": citation
            })

        cleaned_questions = self.shuffle_questions_choices(cleaned_questions)

        return {
            "questions": cleaned_questions[:num_questions]
        }

    def answer_textbook_question(self, textbook_title, question, context, chat_history="", temp=0.2):
        prompt = TEXTBOOK_CHAT_PROMPT.format(
            textbook_title=textbook_title or "Unknown textbook",
            chat_history=chat_history or "None",
            question=question,
            context=context,
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )

        raw_text = self.get_response_text(response)
        data = self.parse_json_response(raw_text)

        if "answer" not in data or not isinstance(data["answer"], str):
            raise ValueError("Response missing 'answer'")
        if "grounded" not in data or not isinstance(data["grounded"], bool):
            raise ValueError("Response missing 'grounded'")

        raw_citations = data.get("citations") or []
        if not isinstance(raw_citations, list):
            raise ValueError("Response field 'citations' must be a list")

        citations = self.normalize_citations(
            list(raw_citations) + self.collect_block_citations(data.get("answer_blocks"))
        )
        answer = self.remove_citations_from_answer(
            data["answer"].strip(),
            citations,
        )
        answer_blocks = self.normalize_answer_blocks(
            data.get("answer_blocks"),
            answer,
            citations,
        )
        final_citations = self.normalize_citations(self.collect_block_citations(answer_blocks)) or citations

        return {
            "answer": self.compose_answer_from_blocks(answer_blocks) or answer,
            "grounded": data["grounded"],
            "citations": final_citations,
            "answer_blocks": answer_blocks,
        }

    def generate_raw(self, prompt, temperature=0.3):
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temperature
        )

        return self.get_response_text(response)
