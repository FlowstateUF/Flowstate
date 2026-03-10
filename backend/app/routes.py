import traceback
import threading, time, traceback
from flask import request, jsonify
from openai import OpenAI
from app.services import create_user, authenticate_user, check_username_exists, check_email_exists, get_user_by_id, upload_textbook_to_supabase, extract_toc, store_toc, LLMService, QUESTION_TYPES, MC_BASE_PROMPT, FLASHCARD_PROMPT, SUMMARY_PROMPT
from app.processing import process_textbook
from app.config import settings
import re
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.clients import qdrant, supabase
from app.services import embed_query

from qdrant_client.models import Filter, FieldCondition, MatchValue

def verify_textbook_owner(user_id: str, textbook_id: str) -> bool:
    res = (
        supabase.table("textbooks")
        .select("id")
        .eq("id", textbook_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def retrieve_context(user_id: str, textbook_id: str, query: str, top_k: int = 8) -> str:
    qvec = embed_query(query)

    flt = Filter(
        must=[
            FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
            FieldCondition(key="textbook_id", match=MatchValue(value=str(textbook_id))),
        ]
    )

    res = qdrant.query_points(
        collection_name="chunks",
        query=qvec,
        using="dense",
        query_filter=flt,
        limit=top_k,
        with_payload=True,
    )

    hits = res.points or []
    if not hits:
        return ""

    parts = []
    for p in hits:
        payload = p.payload or {}
        text = (payload.get("text") or payload.get("content") or "").strip()
        if not text:
            continue

        citation = payload.get("citation")
        if not citation:
            ps = payload.get("page_start") or payload.get("page_number")
            pe = payload.get("page_end")
            if ps is not None:
                citation = f"Page {ps}" if pe in (None, ps) else f"Pages {ps}-{pe}"

        parts.append(f"{citation}: {text}" if citation else text)

    return "\n\n".join(parts)

def _fetch_chapter_chunks(textbook_id: str, chapter_id: str, limit: int = 60) -> list[dict]:
    # Pull the first N chunks in that chapter (ordered)
    res = (
        supabase.table("chunks")
        .select("id, page_number, rindex, content")
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .order("page_number")
        .order("rindex")
        .limit(limit)
        .execute()
    )
    return res.data or []

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

            # Check if this user already uploaded this file
            existing = (
                supabase.table("textbooks")
                .select("id, status")
                .eq("user_id", user_id)
                .eq("title", file.filename)
                .limit(1)
                .execute()
            )

            if existing.data:
                existing_id = existing.data[0]["id"]
                print(f"[upload] '{file.filename}' already parsed before, skipping")

                return jsonify({
                    "status": "exists",
                    "message": "This textbook was already uploaded and parsed",
                    "textbook_id": existing_id
                }), 200
            
            # Upload textbook
            print("[upload] uploading to supabase")
            textbook = upload_textbook_to_supabase(
                user_id=user_id,
                file_bytes=file_bytes,
                filename=file.filename,
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
            
            # TODO: Add celery functionality
            # CELERY: replace with ingest_task.delay(user_id, textbook_id, file_b64)
            # and return 202 immediately instead of waiting
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
        topic = (data.get("topic") or "").strip()

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not verify_textbook_owner(user_id, textbook_id):
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        retrieval_query = topic if topic else "main ideas key terms"
        context = retrieve_context(user_id, textbook_id, retrieval_query, top_k=14)
        if not context.strip():
            return jsonify({"error": "Insufficient context"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)

        result = llm.generate_summary(context=context, temp=0.3)
        return jsonify({"status": "success", **result}), 200

    
    # Add inside register_routes(app):
    @app.post("/api/test-summary-chapter")
    @jwt_required()
    def test_summary_chapter():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        textbook_id = data.get("textbook_id")
        chapter_id = data.get("chapter_id")
        temp = float(data.get("temp", 0.3))

        if not textbook_id or not chapter_id:
            return jsonify({"error": "textbook_id and chapter_id required"}), 400

        # ownership check like your other routes
        owned = (
            supabase.table("textbooks")
            .select("id")
            .eq("id", textbook_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        rows = _fetch_chapter_chunks(textbook_id, chapter_id, limit=80)
        if not rows:
            return jsonify({"error": "No chunks found for that chapter_id"}), 400

        context = _build_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.generate_summary(context=context, temp=temp)

        return jsonify({
            "status": "success",
            "chapter_id": chapter_id,
            "chunks_used": len(rows),
            "context_preview": context[:800],
            **result
        }), 200

    @app.get("/api/debug/qdrant-vectors")
    def debug_qdrant_vectors():
        info = qdrant.get_collection("chunks")
        return jsonify(str(info.config.params.vectors))