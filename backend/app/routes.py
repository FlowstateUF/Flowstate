import threading
from flask import request, jsonify
from openai import OpenAI
from app.services import create_user, authenticate_user, check_username_exists, check_email_exists, get_user_by_id, upload_textbook_to_supabase, extract_toc, store_toc
from app.processing import process_textbook
from app.config import settings
import re
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

# ** Where HTTP routes are written **
# register_routes is called in init.py, giving it access to all the routes below 

def register_routes(app):
    
    @app.get("/")
    def root():
        return jsonify({"message": "Flowstate backend running"})
    

    # ** User Authentication Routes **
    @app.post("/api/register")
    def register_user():
        data = request.get_json(silent=True) or {}

        # Standardize input
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        # Validate user filled in required fields
        if not username or not email or not password:
            return jsonify({"error": "username, email, and password are required"}), 400

        # Username rules
        if len(username) < 3 or len(username) > 20:
            return jsonify({"error": "username must be 3–20 characters"}), 400
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return jsonify({"error": "username can only contain letters, numbers, underscores"}), 400

        # Email requirements
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return jsonify({"error": "invalid email"}), 400

        # Password requirements
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400
        if not re.search(r"[A-Z]", password):
            return jsonify({"error": "password must include an uppercase letter"}), 400
        if not re.search(r"[a-z]", password):
            return jsonify({"error": "password must include a lowercase letter"}), 400
        if not re.search(r"\d", password):
            return jsonify({"error": "password must include a number"}), 400

        # Ensure username and email aren't already being used
        if check_username_exists(username):
            return jsonify({"error": "Username already taken"}), 409
        if check_email_exists(email):
            return jsonify({"error": "Email already in use"}), 409

        try:
            user = create_user(username, password, email)
        except Exception as e:
            return jsonify({"error": "Database error", "details": str(e)}), 500

        return jsonify({
            "status": "success",
            "message": "User registered",
            "user": {"id": user['id'], "username": user['username'], "email": user['email']}
        }), 201

    @app.post("/api/login")
    def login_user():
        data = request.get_json(silent=True) or {}

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = authenticate_user(email, password)

        if "error" in user:
            return jsonify(user), 401

        token = create_access_token(identity=str(user['id']))

        return jsonify({
            "message": "Login successful",
            "access_token": token,
            "user": {"id": user['id'], "username": user['username'], "email": user['email']}
        }), 200

    @app.get("/api/me")
    @jwt_required()
    def me():
        user_id = get_jwt_identity()
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"id": user['id'], "username": user['username'], "email": user['email']}), 200


    # ** Textbook Behavior Routers **
    
    @app.post("/api/upload")
    @jwt_required()
    def upload_textbook():
        user_id = get_jwt_identity()
        file = request.files.get("file")

        if not file:
            return jsonify({"error": "No file uploaded."}), 400

        try:
            file_bytes = file.read()
            # Upload textbook
            textbook = upload_textbook_to_supabase(
                user_id=user_id,
                file_bytes=file_bytes,
                filename=file.filename,
            )
            textbook_id = textbook['id']

            # Extract TOC and store
            toc, total_pages = extract_toc(file_bytes)
            store_toc(textbook_id, toc, total_pages)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        try:
            # Process textbook in background thread
            # thread = threading.Thread(target=process_textbook, args=(textbook_id, file_bytes))
            # thread.daemon = True
            # thread.start()
            process_textbook(user_id, textbook_id, file_bytes)

        except Exception as e:
            return jsonify({"error": "Failed to process textbook", "details": str(e)}), 500

        return jsonify({
            "status": "success",
            "message": "PDF uploaded successfully",
            "textbook_id": textbook['id'],
            "filename": textbook['title'],
            "storage_path": textbook['storage_path']
        }), 200

    # ** NaviGator Routes **

    @app.route("/api/generate", methods=["POST"])
    @jwt_required()
    def generate():
        user_id = get_jwt_identity()

        data = request.get_json(silent=True) or {}
        client = OpenAI(
            api_key=settings.NAVIGATOR_API_KEY,
            base_url="https://api.ai.it.ufl.edu/v1/",
        )

        PROMPT = "Generate me a simple recall question type based on the Array Data Structures. It should be four multiple choice options, ensure there is only one correct answer. Provide a very brief explanation validating the correct answer."

        response = client.responses.create(
            model="gpt-oss-20b",
            input=PROMPT,
        )

        return jsonify({
            "text": response.output_text
        }), 200

