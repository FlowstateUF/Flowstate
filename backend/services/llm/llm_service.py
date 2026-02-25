import json
from openai import OpenAI
from services.llm.question_prompts import MC_BASE_PROMPT, QUESTION_TYPES

# Class that allows us to construct each prompt and recieve output fromt the LLM
class LLMService:
    
    def __init__(self, api_key):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.ai.it.ufl.edu/v1/"
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