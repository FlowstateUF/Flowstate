import hashlib
import re, time, traceback
from flask import request, jsonify
from openai import OpenAI
from app.services.llm_service import LLMService
from app.services.question_prompts import (
    QUESTION_TYPES, 
    MC_BASE_PROMPT, 
    FLASHCARD_PROMPT, 
    SUMMARY_PROMPT
)
from app.services.supabase_service import (
    authenticate_user, 
    check_email_exists, 
    check_pretest_exists,
    check_textbook_exists,
    check_username_exists, 
    create_user, 
    fetch_chapter_chunks,
    get_textbook,
    get_textbook_info,
    get_toc,
    get_user_by_id, 
    list_user_textbooks,
    rename_textbook_for_user,
    delete_textbook_for_user,
    set_textbook_starred_for_user,
    store_toc,
    upload_textbook_to_supabase
)

from app.services.textbook_service import extract_toc
from app.services.vector_service import (
    get_collection_info,
    retrieve_context,
    fetch_all_chunks,
    delete_textbook_chunks,
)

from app.services.textbook_info import(
    display_title,
    serialize_textbook_card
)

from app.processing import process_textbook
from app.config import settings
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity


def _build_context_from_chunks(rows: list[dict], max_chars: int = 12000) -> str:
    parts = []
    total = 0
    for r in rows:
        content = (r.get("content") or "").strip()
        if not content:
            continue
        page = r.get("page_number")
        prefix = f"Page {page}: " if page is not None else ""
        snippet = prefix + content
        if total + len(snippet) > max_chars:
            break
        parts.append(snippet)
        total += len(snippet)
    return "\n\n".join(parts)


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

    @app.get("/api/textbooks")
    @jwt_required()
    def list_textbooks():
        user_id = get_jwt_identity()
        include_all = request.args.get("all", "false").lower() == "true"
        textbooks = list_user_textbooks(user_id)
        payload = [serialize_textbook_card(book) for book in textbooks]
        return jsonify({"textbooks": payload}), 200
    
    @app.post("/api/upload")
    @jwt_required()
    def upload_textbook():
        print("[upload] request received")
        user_id = get_jwt_identity()
        file = request.files.get("file")

        if not file:
            return jsonify({"error": "No file uploaded."}), 400

        try:
            print("[upload] reading file")
            file_bytes = file.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Check if this user already uploaded this file
            existing = check_textbook_exists(user_id, file_hash)

            if existing:
                existing_id = existing["id"]
                print(f"[upload] '{file.filename}' already parsed before, skipping")

                return jsonify({
                    "status": "exists",
                    "message": "This textbook was already uploaded and parsed",
                    "textbook_id": existing_id,
                    "filename": existing.get("title") or file.filename,
                    "display_title": display_title(existing.get("title") or file.filename),
                    "processing_status": existing.get("status") or "processing",
                }), 200
            
            # Upload textbook
            print("[upload] uploading to supabase")
            textbook = upload_textbook_to_supabase(
                user_id=user_id,
                file_bytes=file_bytes,
                filename=file.filename,
                file_hash=file_hash
            )
            textbook_id = textbook['id']

            # Extract TOC and store
            print("[upload] extracting toc")
            toc, total_pages = extract_toc(file_bytes)
            print("[upload] storing toc")
            store_toc(textbook_id, toc, total_pages)

        except Exception as e:
            print("[upload] FAILED:", repr(e))
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

        try:
            process_textbook.delay(user_id, textbook_id, file_bytes)
            # process_textbook(user_id, textbook_id, file_bytes)

        except Exception as e:
            return jsonify({"error": "Failed to process textbook", "details": str(e)}), 500

        return jsonify({
            "status": "success",
            "message": "PDF uploaded successfully",
            "textbook_id": textbook['id'],
            "filename": textbook['title'],
            "display_title": display_title(textbook["title"]),
            "storage_path": textbook['storage_path']
        }), 202
    
    # Get upload progress
    @app.get("/api/textbooks/<textbook_id>/status")
    @jwt_required()
    def get_textbook_status(textbook_id):
        user_id = get_jwt_identity()
        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Not found"}), 404

        info = get_textbook_info(textbook_id)
        return jsonify(serialize_textbook_card(info)), 200
    
    @app.patch("/api/textbooks/<textbook_id>/rename")
    @jwt_required()
    def rename_textbook(textbook_id):
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        new_title = (data.get("title") or "").strip()

        if not new_title:
            return jsonify({"error": "title is required"}), 400

        if len(new_title) > 120:
            return jsonify({"error": "title must be 120 characters or fewer"}), 400

        if "/" in new_title or "\\" in new_title:
            return jsonify({"error": "title cannot contain slashes"}), 400

        updated = rename_textbook_for_user(user_id, textbook_id, new_title)
        if not updated:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        return jsonify(serialize_textbook_card(updated)), 200
    
    @app.patch("/api/textbooks/<textbook_id>/star")
    @jwt_required()
    def star_textbook(textbook_id):
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        is_starred = data.get("is_starred")
        if not isinstance(is_starred, bool):
            return jsonify({"error": "is_starred must be true or false"}), 400

        updated = set_textbook_starred_for_user(user_id, textbook_id, is_starred)
        if not updated:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        return jsonify(serialize_textbook_card(updated)), 200


    @app.delete("/api/textbooks/<textbook_id>")
    @jwt_required()
    def delete_textbook_route(textbook_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        try:
            delete_textbook_chunks(user_id, textbook_id)
        except Exception as e:
            print("[delete_textbook] qdrant cleanup failed:", repr(e))

        deleted = delete_textbook_for_user(user_id, textbook_id)
        if not deleted:
            return jsonify({"error": "Textbook could not be deleted"}), 500

        return jsonify({
            "status": "success",
            "message": "Textbook deleted successfully",
        }), 200
   
   
    @app.get("/api/textbooks/<textbook_id>/chapters")
    @jwt_required()
    def get_textbook_chapters(textbook_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        chapters = get_toc(textbook_id) or []

        return jsonify({
            "chapters": chapters
        }), 200


    # ** NaviGator Routes **

    # test this by using curl '-X POST http://127.0.0.1:5001/api/test-recall' in the terminal after running the Flask app
    # curl.exe -X POST http://127.0.0.1:5001/api/test-recall < powershell 
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

    @app.post("/api/generate/summary")
    @jwt_required()
    def generate_summary():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        textbook_id = data.get("textbook_id")
        chapter_title = (data.get("chapter_title") or "").strip()

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        points = fetch_all_chunks(textbook_id=textbook_id, chapter_title=chapter_title, user_id=user_id)
        if not points:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        rows = []
        for p in points:
            payload = p.payload or {}
            rows.append({
                "content": payload.get("text") or payload.get("content") or "",
                "page_number": payload.get("page_number") or payload.get("page_start"),
            })

        context = _build_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.generate_summary(context=context, temp=0.3)

        return jsonify({
            "status": "success",
            "textbook_id": textbook_id,
            "chapter_title": chapter_title,
            "chunks_used": len(rows),
            **result
        }), 200


    @app.post("/api/generate/flashcards")
    @jwt_required()
    def generate_flashcards():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        textbook_id = data.get("textbook_id")
        chapter_title = (data.get("chapter_title") or "").strip()
        num_cards = int(data.get("num_cards") or 5)

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400

        if num_cards < 1 or num_cards > 15:
            return jsonify({"error": "num_cards must be between 1 and 15"}), 400

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        points = fetch_all_chunks(
            textbook_id=textbook_id,
            chapter_title=chapter_title,
            user_id=user_id
        )

        if not points:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        rows = []
        for p in points:
            payload = p.payload or {}
            rows.append({
                "content": payload.get("text") or payload.get("content") or "",
                "page_number": payload.get("page_number") or payload.get("page_start"),
            })

        context = _build_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.generate_flashcards(
            context=context,
            num_cards=num_cards,
            temp=0.3
        )

        return jsonify({
            "status": "success",
            "textbook_id": textbook_id,
            "chapter_title": chapter_title,
            "flashcards": result.get("flashcards", [])
        }), 200
    

    @app.post("/api/generate/quiz")
    @jwt_required()
    def generate_quiz():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        textbook_id = data.get("textbook_id")
        chapter_title = (data.get("chapter_title") or "").strip()
        difficulty = str(data.get("difficulty") or "1")
        num_questions = int(data.get("num_questions") or 5)

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400

        difficulty_map = {
            "1": "recall",
            "2": "understand",
            "3": "apply",
            "4": "analyze",
            "recall": "recall",
            "understand": "understand",
            "apply": "apply",
            "analyze": "analyze",
        }

        question_type = difficulty_map.get(difficulty)
        if not question_type:
            return jsonify({"error": "difficulty must be 1-4 or a valid type"}), 400

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        points = fetch_all_chunks(
            textbook_id=textbook_id,
            chapter_title=chapter_title,
            user_id=user_id
        )

        if not points:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        rows = []
        for p in points:
            payload = p.payload or {}
            rows.append({
                "content": payload.get("text") or payload.get("content") or "",
                "page_number": payload.get("page_number") or payload.get("page_start"),
            })

        context = _build_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)

        result = llm.generate_quiz(
            context=context,
            question_type=question_type,
            num_questions=num_questions,
            temp=0.3
        )

        return jsonify({
            "status": "success",
            "difficulty": difficulty,
            "question_type": question_type,
            "questions": result["questions"]
        }), 200