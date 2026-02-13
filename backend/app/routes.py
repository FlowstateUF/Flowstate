from flask import request, jsonify
from services import upload_doc_to_supabase, create_document_record
from openai import OpenAI
from app.config import settings

# ** Where HTTP routes are written **

# register_routes is called in init.py, giving it access to all the routes below 
def register_routes(app):
    
    @app.get("/")
    def root():
        return jsonify({"message": "Flowstate backend running"})
    
    @app.post("/api/upload")
    def upload_document():
        file = request.files.get("file")
        # user_id = request.form.get("user_id")
        user_id = 1 # Placeholder

        if not file:
            return jsonify({"error": "No file uploaded."}), 400
        
        try:
            # Upload to Supabase Storage
            storage_path = upload_doc_to_supabase(
                user_id=user_id,
                file_bytes=file.read(),
                filename=file.filename
            )

            # Create DB record
            doc = create_document_record(
                user_id=user_id,
                filename=file.filename,
                storage_path=storage_path
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({
            "status": "success",
            "message": "PDF uploaded successfully",
            "document_id": doc.id,
            "filename": doc.filename,
            "storage_path": storage_path
        }), 200

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
