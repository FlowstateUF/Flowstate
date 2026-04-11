import json, random, re
from openai import OpenAI
from .question_prompts import (
    MC_BASE_PROMPT,
    QUESTION_TYPES,
    FLASHCARD_PROMPT,
    SUMMARY_PROMPT,
    PRETEST_PROMPT,
    TEXTBOOK_CHAT_PROMPT,
)

# Class that allows us to construct each prompt and recieve output fromt the LLM
class LLMService:
    
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.ai.it.ufl.edu"
        )
        self.model = "gpt-oss-20b"

    # Used to construct the LLM prompt with the provided context and question type
    def _build_prompt(self, context, question_type, temp):
        
        # Check if question type exists
        if question_type not in QUESTION_TYPES:
            raise ValueError(f"Unknown question type: {question_type}")
        
        # Fill in the template
        return MC_BASE_PROMPT.format(
            context=context,
            question_instructions=QUESTION_TYPES[question_type]
        )
    
    # Parses the JSON output provided from the LLM
    def _parse_response(self, response_text):
        
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
        
    # Parse JSON for flashcards and summaries    
    def _parse_json(self, response_text: str):
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
    
    def _get_response_text(self, response) -> str:
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

    def questionHasExternalReference(self, question_text: str) -> bool:
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

    def validatePretestQuestion(self, question: dict, index: int):
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

        if self.questionHasExternalReference(prompt_text):
            raise ValueError(
                f"Question {index} is not self-contained and appears to reference hidden external material: {prompt_text}"
            )

    def validatePretestQuestions(self, questions: list[dict], expected_count: int):
        if len(questions) != expected_count:
            raise ValueError(f"Expected {expected_count} questions, got {len(questions)}")

        for i, question in enumerate(questions):
            self.validatePretestQuestion(question, i)

    # Generates a question using the given context and question type
    def generate_question(self, context, question_type, temp):

        # Build the prompt
        prompt = self._build_prompt(context, question_type, temp)
        
        # Call the LLM
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )
        
        # Parse and return the result
        return self._parse_response(response.output_text)

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

        data = self._parse_json(response.output_text)

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

        raw_text = self._get_response_text(response)
        data = self._parse_json(raw_text)
        # data = self._parse_json(response.output_text)

        if "summary" not in data or not isinstance(data["summary"], dict):
            raise ValueError("Response missing 'summary' object")

        return data
    
    #STOPPED USING
    # # Extracts the core topics from a given chapter: helps with question labeling
    # def extract_chapter_topics(self, context, temp=0.2):
    #     prompt = TOPIC_EXTRACTION_PROMPT.format(context=context)

    #     response = self.client.responses.create(
    #         model=self.model,
    #         input=prompt,
    #         temperature=temp
    #     )

    #     data = self._parse_json(response.output_text)

    #     if "topics" not in data or not isinstance(data["topics"], list):
    #         raise ValueError("Response missing 'topics' list")
    #     if not (5 <= len(data["topics"]) <= 10):
    #         print(f"[topics] warning: got {len(data['topics'])} topics (expected 5-10)")

    #     return data["topics"]
    
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

            data = self._parse_json(response.output_text)

            if "questions" not in data or not isinstance(data["questions"], list):
                raise ValueError("Response missing 'questions' list")

            try:
                self.validatePretestQuestions(data["questions"], PRETEST_Q_COUNT)
                return self.shuffleQuestionsChoices(data["questions"])
            except ValueError as exc:
                last_error = exc
                print(f"[pretest] validation failed on attempt {attempt + 1}: {exc}")

        raise last_error or ValueError("Pretest generation failed validation")

    def shuffleQuestionChoices(self, question: dict) -> dict:
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

    def shuffleQuestionsChoices(self, questions: list[dict]) -> list[dict]:
        return [self.shuffleQuestionChoices(question) for question in questions]
    
    def generate_quiz(self, context, question_type="recall", num_questions=5, temp=0.3):
        questions = []
        # adjust for duplicate questions later

        for _ in range(num_questions):
            q = self.generate_question(
                context=context,
                question_type=question_type,
                temp=temp
            )
            questions.append({
                **q,
                "type": question_type,
            })

        return {
            "questions": questions
        }

    def answer_textbook_question(self, textbook_title, question, context, temp=0.2):
        prompt = TEXTBOOK_CHAT_PROMPT.format(
            textbook_title=textbook_title or "Unknown textbook",
            question=question,
            context=context,
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )

        raw_text = self._get_response_text(response)
        data = self._parse_json(raw_text)

        if "answer" not in data or not isinstance(data["answer"], str):
            raise ValueError("Response missing 'answer'")
        if "grounded" not in data or not isinstance(data["grounded"], bool):
            raise ValueError("Response missing 'grounded'")

        citations = data.get("citations") or []
        if not isinstance(citations, list):
            raise ValueError("Response field 'citations' must be a list")

        return {
            "answer": data["answer"].strip(),
            "grounded": data["grounded"],
            "citations": [str(citation).strip() for citation in citations if str(citation).strip()],
        }
