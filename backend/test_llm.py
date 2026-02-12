import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv() 

api_key = os.getenv("NAVIGATOR_TOOLKIT_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.ai.it.ufl.edu/v1/",
)

response = client.responses.create(
    model="gpt-oss-20b",
    input="Say hello in one sentence and tell me the definition of a square.",
)

print(response.output_text)
