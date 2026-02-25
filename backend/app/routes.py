from flask import request, jsonify
from services import upload_doc_to_supabase, create_document_record, LLMService, QUESTION_TYPES
from openai import OpenAI
from app.config import settings
from app.db import db
from app.models import User
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
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "username already taken"}), 409
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "email already in use"}), 409

        # Create user + hash password
        user = User(username=username, email=email)
        user.set_password(password)  

        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500

        return jsonify({
            "status": "success",
            "message": "User registered",
            "user": {"id": user.id, "username": user.username, "email": user.email}
        }), 201

    @app.post("/api/login")
    def login_user():
        data = request.get_json(silent=True) or {}

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401

        token = create_access_token(identity=str(user.id))

        return jsonify({
            "message": "Login successful",
            "access_token": token,
            "user": {"id": user.id, "username": user.username}
        }), 200

    @app.get("/api/me")
    @jwt_required()
    def me():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"id": user.id, "username": user.username, "email": user.email}), 200


    # ** Textbook Behavior Routers **
    
    @app.post("/api/upload")
    @jwt_required()
    def upload_document():
        user_id = get_jwt_identity()
        file = request.files.get("file")

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

    # ** NaviGator Routes **

    # test this by using curl '-X POST http://127.0.0.1:5001/api/test-recall' in the terminal after running the Flask app
    @app.post("/api/test-recall")
    def test_recall():
        from app.config import settings

        # Hardcoded context
        context = """
        An array is a linear data structure that stores elements in contiguous memory locations.
        Each element can be accessed using its index. Arrays typically have a fixed size once created.
        Accessing an element by index is O(1) time complexity. Page 20.
        """

        try:
            llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
            question = llm.generate_question(
                context=context,
                question_type="recall",
                temp = 0.3
            )

            return jsonify({
                "status": "success",
                "question": question
            }), 200

        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500

