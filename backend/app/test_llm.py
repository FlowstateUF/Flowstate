from openai import OpenAI
from app.config import settings


def main():

    client = OpenAI(
        api_key=settings.NAVIGATOR_API_KEY,
        base_url="https://api.ai.it.ufl.edu/v1/",  
    )

    response = client.responses.create(
        model="gpt-oss-20b",
        input="Say hello in one sentence and tell me the definition of a square.",
    )

    # to test go to /backend and enter python -m app.test_llm
    print(response.output_text)


if __name__ == "__main__":
    main()
