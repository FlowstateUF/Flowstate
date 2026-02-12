from flask import jsonify
from openai import OpenAI
from app.config import settings

# ** Where HTTP routes are written **

# register_routes is called in init.py, giving it access to all the routes below 
def register_routes(app):
    
    @app.get("/")
    def root():
        return jsonify({"message": "Flowstate backend running"})

    @app.route("/api/generate", methods=["GET", "POST"])
    def generate():

        client = OpenAI(
            api_key=settings.NAVIGATOR_API_KEY,
            base_url="https://api.ai.it.ufl.edu/v1/",
        )

        PROMPT = "Say hello and tell me the definition of a square."

        response = client.responses.create(
            model="gpt-oss-20b",
            input=PROMPT,
        )

        return jsonify({
            "text": response.output_text
        })
