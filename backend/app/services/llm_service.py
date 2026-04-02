import json, re
from openai import OpenAI
from .question_prompts import MC_BASE_PROMPT, QUESTION_TYPES, FLASHCARD_PROMPT, SUMMARY_PROMPT, PRETEST_PROMPT

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

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=temp
        )

        data = self._parse_json(response.output_text)

        if "questions" not in data or not isinstance(data["questions"], list):
            raise ValueError("Response missing 'questions' list")
        
        # Retry once if count is wrong
        if len(data["questions"]) != PRETEST_Q_COUNT:
            print(f"[pretest] got {len(data['questions'])} questions, retrying...")
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=temp
            )
            data = self._parse_json(response.output_text)
        
        if len(data["questions"]) != PRETEST_Q_COUNT:
            raise ValueError(f"Expected {PRETEST_Q_COUNT} questions, got {len(data['questions'])}")

        required = ["type", "question", "choices", "correct_answer", "explanation", "citation"]
        for i, q in enumerate(data["questions"]):
            missing = [f for f in required if f not in q]
            if missing:
                raise ValueError(f"Question {i} missing fields: {missing}")
        
            valid_types = {"recall", "understand", "apply", "analyze"}
            if q["type"] not in valid_types:
                raise ValueError(f"Question {i} has invalid type: {q['type']}")
        

        return data["questions"]
    
    def generate_quiz(self, context, question_type="recall", num_questions=5, temp=0.3):
        questions = []
        # adjust for duplicate questions later

        for _ in range(num_questions):
            q = self.generate_question(
                context=context,
                question_type=question_type,
                temp=temp
            )
            questions.append(q)

        return {
            "questions": questions
        }