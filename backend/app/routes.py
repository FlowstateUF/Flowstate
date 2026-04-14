import hashlib, re, time, traceback
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
    get_chapter,
    get_pretest,
    get_pretest_attempt,
    get_textbook,
    get_textbook_info,
    get_textbook_dashboard_snapshot,
    get_toc,
    get_user_by_id, 
    list_user_textbooks,
    save_pretest_attempt_progress,
    rename_textbook_for_user,
    delete_textbook_for_user,
    set_textbook_starred_for_user,
    complete_pretest_attempt,
    store_toc,
    upload_textbook_to_supabase,
    create_flashcard_set,
    add_flashcard,
    create_quiz,
    add_quiz_question,
    create_summary,
    submit_quiz_attempt,
    store_flashcard_session,
    store_summary_session,
    quiz_owned_by_user,
    flashcard_set_owned_by_user,
    summary_owned_by_user,
)

from app.services.textbook_helpers import (
    apply_display_page_labels,
    build_chapter_range_response,
    display_page_to_physical_page,
    filter_rows_for_chapter_content,
    find_chapter_by_title,
    find_referenced_chapter,
)
from app.services.textbook_service import extract_toc
from app.services.vector_service import (
    get_collection_info,
    retrieve_context,
    retrieve_relevant_chunks,
    fetch_all_chunks,
    fetch_page_chunks,
    delete_textbook_chunks,
)

from app.services.textbook_info import(
    display_title,
    serialize_textbook_card
)

from app.processing import process_textbook
from app.config import settings
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity


# Builds the upload-limit message users see for oversized PDFs.
def get_textbook_upload_limit_mb() -> int:
    return 50


# Converts the upload cap into bytes for file checks.
def get_textbook_upload_limit_bytes() -> int:
    return get_textbook_upload_limit_mb() * 1000 * 1000


# Builds the upload-limit message users see for oversized PDFs.
def build_upload_limit_message(file_size_bytes: int | None = None) -> str:
    upload_limit_mb = get_textbook_upload_limit_mb()

    if isinstance(file_size_bytes, int) and file_size_bytes > 0:
        file_size_mb = file_size_bytes / (1000 * 1000)
        return (
            f"This PDF is {file_size_mb:.1f} MB, but uploads are capped at {upload_limit_mb} MB right now. "
            f"Until founders update services, please upload a file under {upload_limit_mb} MB."
        )

    return (
        f"Uploads are capped at {upload_limit_mb} MB right now. "
        f"Until founders update services, please upload a file under {upload_limit_mb} MB."
    )


def build_study_context_from_chunks(
    rows: list[dict],
    max_chars: int = 12000,
    bucket_count: int = 4,
) -> str:
    prepared = []

    for index, row in enumerate(rows):
        content = (row.get("content") or "").strip()
        if not content:
            continue

        page = row.get("page_number")
        prefix = f"Page {page}: " if page is not None else ""
        snippet = prefix + content

        prepared.append({
            "index": index,
            "page_number": page if isinstance(page, int) else None,
            "snippet": snippet,
        })

    if not prepared:
        return ""

    full_context = "\n\n".join(item["snippet"] for item in prepared)
    if len(full_context) <= max_chars:
        return full_context

    bucket_total = max(1, min(bucket_count, len(prepared)))
    page_numbers = [item["page_number"] for item in prepared if item["page_number"] is not None]
    buckets = [[] for _ in range(bucket_total)]

    if page_numbers:
        min_page = min(page_numbers)
        max_page = max(page_numbers)
        span = max(1, ((max_page - min_page) + bucket_total) // bucket_total)

        for item in prepared:
            page = item["page_number"]
            if page is None:
                bucket_index = min(bucket_total - 1, (item["index"] * bucket_total) // len(prepared))
            else:
                bucket_index = min(bucket_total - 1, (page - min_page) // span)
            buckets[bucket_index].append(item)
    else:
        for item in prepared:
            bucket_index = min(bucket_total - 1, (item["index"] * bucket_total) // len(prepared))
            buckets[bucket_index].append(item)

    selected_indices = set()
    positions = [0] * bucket_total
    total_chars = 0

    while True:
        added_this_round = False

        for bucket_index, bucket in enumerate(buckets):
            while positions[bucket_index] < len(bucket):
                item = bucket[positions[bucket_index]]
                positions[bucket_index] += 1

                if item["index"] in selected_indices:
                    continue

                separator_chars = 2 if selected_indices else 0
                snippet_len = len(item["snippet"])
                if total_chars + separator_chars + snippet_len > max_chars:
                    break

                selected_indices.add(item["index"])
                total_chars += separator_chars + snippet_len
                added_this_round = True
                break

        if not added_this_round:
            break

    if not selected_indices:
        return prepared[0]["snippet"][:max_chars].strip()

    selected = [
        item["snippet"]
        for item in prepared
        if item["index"] in selected_indices
    ]
    return "\n\n".join(selected)


def build_chat_context(rows: list[dict], max_chars: int = 10000) -> str:
    parts = []
    total = 0

    for idx, row in enumerate(rows, start=1):
        content = (row.get("content") or "").strip()
        if not content:
            continue

        citation = row.get("citation") or (f"Page {row.get('page_number')}" if row.get("page_number") is not None else None)
        chapter = row.get("chapter")

        prefix_bits = [f"Source {idx}"]
        if chapter:
            prefix_bits.append(f"Chapter: {chapter}")
        if citation:
            prefix_bits.append(f"Citation: {citation}")

        snippet = " | ".join(prefix_bits) + f"\n{content}"
        if total + len(snippet) > max_chars:
            break

        parts.append(snippet)
        total += len(snippet)

    return "\n\n".join(parts)


def serialize_chat_sources(rows: list[dict], limit: int = 4) -> list[dict]:
    return [
        {
            "citation": row.get("citation"),
            "chapter": row.get("chapter"),
            "page_number": row.get("display_page_label") or row.get("page_number"),
            "content": row.get("content"),
            "score": row.get("score"),
        }
        for row in rows[:limit]
    ]

# Pulls a page number out when the user asks for one.
def extract_requested_page_number(message: str) -> int | None:
    match = re.search(r"\bpage\s+(\d+)\b", (message or "").strip().lower(), re.IGNORECASE)
    if not match:
        return None

    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None

# Packs recent chat turns into a short context string.
def build_recent_chat_history(history: list[dict], limit: int = 6) -> str:
    lines = []

    for item in (history or [])[-limit:]:
        if not isinstance(item, dict):
            continue
        role = "student" if item.get("role") == "user" else "flo"
        text = (item.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"{role.title()}: {text}")

    return "\n".join(lines)

# Adds recent chat to retrieval so follow-ups stay grounded.
def build_retrieval_query(message: str, history: list[dict]) -> str:
    normalized = (message or "").strip()
    if not normalized:
        return ""

    recent_history = build_recent_chat_history(history, limit=4)
    return f"{recent_history}\nCurrent question: {normalized}".strip() if recent_history else normalized


def is_chapter_overview_query(message: str) -> bool:
    normalized_message = (message or "").strip().lower()
    overview_keywords = [
        "summarize",
        "summary",
        "what is",
        "what's",
        "what is chapter",
        "what is this chapter",
        "about",
        "overview",
        "main idea",
        "core idea",
        "core concepts",
        "key concepts",
        "concepts",
        "topics covered",
        "list of concepts",
        "give me a list",
    ]
    return any(keyword in normalized_message for keyword in overview_keywords)


def is_chapter_range_query(message: str) -> bool:
    normalized_message = (message or "").strip().lower()
    range_keywords = [
        "what page",
        "what pages",
        "which page",
        "which pages",
        "page range",
        "pages does",
        "pages is",
        "starts on",
        "start on",
        "start page",
        "begin on",
        "begins on",
        "end page",
        "ends on",
        "span",
        "spans",
    ]
    return any(keyword in normalized_message for keyword in range_keywords)

# Packs raw qdrant hits into the shape the chat flow expects.
def rows_from_qdrant_points(points: list, chapter: dict | None = None) -> list[dict]:
    rows = []
    chapter_start = chapter.get("start_page") if chapter else None
    chapter_end = chapter.get("end_page") if chapter else None

    for point in points:
        payload = point.payload or {}
        content = (payload.get("text") or payload.get("content") or "").strip()
        if not content:
            continue

        page_number = payload.get("page_number") or payload.get("page_start")
        if (
            chapter_start is not None and chapter_end is not None and isinstance(page_number, int)
            and (page_number < chapter_start or page_number > chapter_end)
        ):
            continue

        citation = payload.get("citation")
        if not citation and page_number is not None:
            page_end = payload.get("page_end")
            citation = f"Page {page_number}" if page_end in (None, page_number) else f"Pages {page_number}-{page_end}"

        rows.append({
            "content": content,
            "citation": citation,
            "page_number": page_number,
            "page_end": payload.get("page_end"),
            "chapter": payload.get("chapter"),
            "score": getattr(point, "score", None),
        })

    return rows

# Pulls all chunks for one chapter in page order.
def build_chapter_scoped_rows(textbook_id: str, chapter_title: str, user_id: str) -> tuple[list[dict], dict | None]:
    chapters = get_toc(textbook_id) or []
    matched_chapter = find_chapter_by_title(chapter_title, chapters)

    points = fetch_all_chunks(
        textbook_id=textbook_id,
        chapter_title=chapter_title,
        user_id=user_id
    )

    rows = rows_from_qdrant_points(points, matched_chapter)
    rows = apply_display_page_labels(rows, chapters)
    rows = sorted(rows, key=lambda row: row.get("page_number") or 0)
    return rows, matched_chapter


# Shapes a saved pretest attempt for the frontend.
def serialize_pretest_attempt(attempt: dict | None) -> dict | None:
    if not attempt:
        return None

    responses = attempt.get("responses") or []
    total_questions = int(attempt.get("total_questions") or len(responses))
    draft_answers = attempt.get("draft_answers") or []
    status = attempt.get("status") or ("completed" if responses else "in_progress")

    return {
        "id": attempt.get("id"),
        "status": status,
        "score": int(attempt.get("score") or 0),
        "total_questions": total_questions,
        "responses": responses,
        "draft_answers": draft_answers,
        "current_question_index": int(attempt.get("current_question_index") or 0),
        "started_at": attempt.get("started_at") or attempt.get("created_at"),
        "completed_at": attempt.get("completed_at") or (attempt.get("created_at") if status == "completed" else None),
    }


def normalizeConfidenceLabel(raw_confidence) -> str | None:
    if not isinstance(raw_confidence, str):
        return None

    normalized = raw_confidence.strip().lower()
    return normalized if normalized in {"low", "medium", "high"} else None


# Scores the submitted answers and builds the response breakdown.
def score_pretest_attempt(questions: list[dict], answers: list, confidences: list | None = None) -> tuple[int, list[dict]]:
    answer_labels = ["A", "B", "C", "D"]
    responses = []
    score = 0

    for idx, question in enumerate(questions):
        choices = question.get("choices") or {}
        raw_answer = answers[idx] if idx < len(answers) else None
        raw_confidence = confidences[idx] if isinstance(confidences, list) and idx < len(confidences) else None
        selected_answer = raw_answer.strip().upper() if isinstance(raw_answer, str) else None
        confidence = normalizeConfidenceLabel(raw_confidence)

        if selected_answer not in answer_labels:
            selected_answer = None

        correct_answer = (question.get("correct_answer") or "").strip().upper()
        is_correct = selected_answer == correct_answer
        if is_correct:
            score += 1

        responses.append({
            "questionIndex": idx,
            "title": f"Question {idx + 1}",
            "prompt": question.get("question") or "",
            "selectedAnswer": selected_answer,
            "selectedText": choices.get(selected_answer) if selected_answer else None,
            "correctAnswer": correct_answer or None,
            "correctText": choices.get(correct_answer) if correct_answer else None,
            "isCorrect": is_correct,
            "type": question.get("type"),
            "confidence": confidence,
            "citation": question.get("citation"),
            "explanation": question.get("explanation"),
        })

    return score, responses


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
        textbooks = list_user_textbooks(user_id, include_all=include_all)
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
            if len(file_bytes) > get_textbook_upload_limit_bytes():
                return jsonify({
                    "error": build_upload_limit_message(len(file_bytes)),
                    "limit_mb": get_textbook_upload_limit_mb(),
                }), 413

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
            error_text = str(e)
            if "payload too large" in error_text.lower() or "maximum allowed size" in error_text.lower():
                return jsonify({
                    "error": build_upload_limit_message(),
                    "limit_mb": get_textbook_upload_limit_mb(),
                }), 413
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

    @app.get("/api/textbooks/<textbook_id>/ask-flo")
    @jwt_required()
    def get_textbook_chat_info(textbook_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        textbook = get_textbook_info(textbook_id)
        if not textbook:
            return jsonify({"error": "Textbook not found"}), 404

        return jsonify({
            "textbook_id": str(textbook.get("id")),
            "textbook_title": display_title(textbook.get("title") or "Untitled textbook"),
            "status": textbook.get("status"),
            "can_chat": textbook.get("status") == "ready",
            "scope": "textbook",
        }), 200

    @app.post("/api/textbooks/<textbook_id>/ask-flo/query")
    @jwt_required()
    def ask_flo_query(textbook_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        textbook = get_textbook_info(textbook_id)
        if not textbook:
            return jsonify({"error": "Textbook not found"}), 404

        if textbook.get("status") != "ready":
            return jsonify({"error": "Textbook is still processing"}), 409

        data = request.get_json(silent=True) or {}
        message = (data.get("message") or "").strip()
        history = data.get("history") if isinstance(data.get("history"), list) else []
        top_k = int(data.get("top_k") or 6)

        if not message:
            return jsonify({"error": "message is required"}), 400

        if len(message) > 2000:
            return jsonify({"error": "message must be 2000 characters or fewer"}), 400

        top_k = max(3, min(top_k, 10))

        chapters = get_toc(textbook_id) or []
        matched_chapter = find_referenced_chapter(message, chapters)
        recent_chat_history = build_recent_chat_history(history)
        retrieval_query = build_retrieval_query(message, history)

        if matched_chapter and is_chapter_range_query(message):
            answer, citations = build_chapter_range_response(matched_chapter, chapters)
            return jsonify({
                "status": "success",
                "textbook_id": str(textbook_id),
                "textbook_title": display_title(textbook.get("title") or "Untitled textbook"),
                "message": answer,
                "answer_blocks": [{
                    "type": "paragraph",
                    "text": answer,
                    "citations": citations,
                }],
                "grounded": True,
                "citations": citations,
                "sources": [],
                "matched_chapter": matched_chapter,
            }), 200

        if matched_chapter and is_chapter_overview_query(message):
            points = fetch_all_chunks(
                textbook_id=str(textbook_id),
                chapter_title=matched_chapter.get("title"),
                user_id=str(user_id),
            )
            points = sorted(points, key=lambda point: ((point.payload or {}).get("page_start") or 0))
            rows = rows_from_qdrant_points(points, matched_chapter)
            rows = apply_display_page_labels(rows, chapters)
            rows = filter_rows_for_chapter_content(rows)
        else:
            chapter_title = matched_chapter.get("title") if matched_chapter else None
            requested_page = extract_requested_page_number(message)
            if requested_page is not None:
                physical_page = display_page_to_physical_page(requested_page, chapters)
                points = fetch_page_chunks(
                    textbook_id=str(textbook_id),
                    user_id=str(user_id),
                    page_number=physical_page if physical_page is not None else requested_page,
                )
                rows = rows_from_qdrant_points(points, matched_chapter)
                rows = apply_display_page_labels(rows, chapters)
                if matched_chapter:
                    rows = filter_rows_for_chapter_content(rows)
            else:
                rows = []

            if not rows:
                rows = retrieve_relevant_chunks(
                    user_id=str(user_id),
                    textbook_id=str(textbook_id),
                    query=retrieval_query or message,
                    top_k=top_k,
                    chapter_title=chapter_title,
                )
                rows = apply_display_page_labels(rows, chapters)
                if matched_chapter:
                    rows = filter_rows_for_chapter_content(rows)

        if not rows:
            return jsonify({
                "status": "success",
                "textbook_id": str(textbook_id),
                "textbook_title": display_title(textbook.get("title") or "Untitled textbook"),
                "message": "I’m not sure this textbook clearly covers that. Try asking about a specific concept, definition, or example from the book.",
                "answer_blocks": [{
                    "type": "paragraph",
                    "text": "I’m not sure this textbook clearly covers that. Try asking about a specific concept, definition, or example from the book.",
                    "citations": [],
                }],
                "grounded": False,
                "citations": [],
                "sources": [],
                "matched_chapter": matched_chapter,
            }), 200

        context = build_chat_context(rows, max_chars=14000 if matched_chapter and is_chapter_overview_query(message) else 10000)
        if not context.strip():
            return jsonify({
                "status": "success",
                "textbook_id": str(textbook_id),
                "textbook_title": display_title(textbook.get("title") or "Untitled textbook"),
                "message": "I found matching textbook chunks, but they were not clear enough to answer confidently.",
                "answer_blocks": [{
                    "type": "paragraph",
                    "text": "I found matching textbook chunks, but they were not clear enough to answer confidently.",
                    "citations": [],
                }],
                "grounded": False,
                "citations": [],
                "sources": serialize_chat_sources(rows),
                "matched_chapter": matched_chapter,
            }), 200

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.answer_textbook_question(
            textbook_title=display_title(textbook.get("title") or "Untitled textbook"),
            question=message,
            context=context,
            chat_history=recent_chat_history,
            temp=0.2,
        )

        return jsonify({
            "status": "success",
            "textbook_id": str(textbook_id),
            "textbook_title": display_title(textbook.get("title") or "Untitled textbook"),
            "message": result.get("answer"),
            "answer_blocks": result.get("answer_blocks", []),
            "grounded": result.get("grounded"),
            "citations": result.get("citations", []),
            "sources": serialize_chat_sources(rows),
            "matched_chapter": matched_chapter,
        }), 200

    @app.get("/api/textbooks/<textbook_id>/chapters/<chapter_id>/pretest/status")
    @jwt_required()
    def get_pretest_status(textbook_id, chapter_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        chapter = get_chapter(textbook_id, chapter_id)
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404

        pretest = get_pretest(textbook_id, chapter_id)
        attempt = get_pretest_attempt(user_id, textbook_id, chapter_id)
        attempt_payload = serialize_pretest_attempt(attempt)

        return jsonify({
            "chapter_id": chapter_id,
            "chapter_title": chapter.get("title"),
            "pretest_ready": bool(pretest and pretest.get("questions")),
            "question_count": len(pretest.get("questions") or []) if pretest else 0,
            "completed": bool(attempt_payload and attempt_payload.get("status") == "completed"),
            "quiz_unlocked": bool(attempt_payload and attempt_payload.get("status") == "completed"),
            "attempt": attempt_payload,
        }), 200

    @app.get("/api/textbooks/<textbook_id>/chapters/<chapter_id>/pretest")
    @jwt_required()
    def get_pretest_for_chapter(textbook_id, chapter_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        chapter = get_chapter(textbook_id, chapter_id)
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404

        pretest = get_pretest(textbook_id, chapter_id)
        if not pretest:
            return jsonify({"error": "Pretest not available for this chapter yet"}), 404

        attempt = get_pretest_attempt(user_id, textbook_id, chapter_id)

        attempt_payload = serialize_pretest_attempt(attempt)

        return jsonify({
            "chapter_id": chapter_id,
            "chapter_title": chapter.get("title"),
            "completed": bool(attempt_payload and attempt_payload.get("status") == "completed"),
            "pretest_id": pretest.get("id"),
            "question_count": len(pretest.get("questions") or []),
            "questions": [] if attempt_payload and attempt_payload.get("status") == "completed" else (pretest.get("questions") or []),
            "attempt": attempt_payload,
        }), 200

    @app.post("/api/textbooks/<textbook_id>/chapters/<chapter_id>/pretest/progress")
    @jwt_required()
    def save_pretest_progress(textbook_id, chapter_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        chapter = get_chapter(textbook_id, chapter_id)
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404

        pretest = get_pretest(textbook_id, chapter_id)
        if not pretest:
            return jsonify({"error": "Pretest not available for this chapter yet"}), 404

        existing_attempt = get_pretest_attempt(user_id, textbook_id, chapter_id)
        existing_payload = serialize_pretest_attempt(existing_attempt)
        if existing_payload and existing_payload.get("status") == "completed":
            return jsonify({
                "error": "Pretest already completed for this chapter",
                "attempt": existing_payload,
            }), 409

        data = request.get_json(silent=True) or {}
        answers = data.get("answers")
        current_question_index = data.get("current_question_index", 0)
        questions = pretest.get("questions") or []

        if not isinstance(answers, list):
            return jsonify({"error": "answers must be an array"}), 400

        if len(answers) != len(questions):
            return jsonify({"error": "answers must include one response per question"}), 400

        if not isinstance(current_question_index, int):
            return jsonify({"error": "current_question_index must be an integer"}), 400

        current_question_index = max(0, min(current_question_index, max(len(questions) - 1, 0)))

        attempt = save_pretest_attempt_progress(
            user_id=str(user_id),
            textbook_id=str(textbook_id),
            chapter_id=str(chapter_id),
            pretest_id=str(pretest.get("id")),
            total_questions=len(questions),
            draft_answers=answers,
            current_question_index=current_question_index,
        )

        return jsonify({
            "status": "success",
            "chapter_id": chapter_id,
            "chapter_title": chapter.get("title"),
            "attempt": serialize_pretest_attempt(attempt),
        }), 200

    @app.post("/api/textbooks/<textbook_id>/chapters/<chapter_id>/pretest/submit")
    @jwt_required()
    def submit_pretest_for_chapter(textbook_id, chapter_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        chapter = get_chapter(textbook_id, chapter_id)
        if not chapter:
            return jsonify({"error": "Chapter not found"}), 404

        pretest = get_pretest(textbook_id, chapter_id)
        if not pretest:
            return jsonify({"error": "Pretest not available for this chapter yet"}), 404

        existing_attempt = get_pretest_attempt(user_id, textbook_id, chapter_id)
        existing_payload = serialize_pretest_attempt(existing_attempt)
        if existing_payload and existing_payload.get("status") == "completed":
            return jsonify({
                "error": "Pretest already completed for this chapter",
                "attempt": existing_payload,
            }), 409

        data = request.get_json(silent=True) or {}
        answers = data.get("answers")
        confidences = data.get("confidences")
        questions = pretest.get("questions") or []

        if not isinstance(answers, list):
            return jsonify({"error": "answers must be an array"}), 400

        if len(answers) != len(questions):
            return jsonify({"error": "answers must include one response per question"}), 400

        if confidences is not None:
            if not isinstance(confidences, list):
                return jsonify({"error": "confidences must be an array when provided"}), 400
            if len(confidences) != len(questions):
                return jsonify({"error": "confidences must include one response per question"}), 400

        score, responses = score_pretest_attempt(questions, answers, confidences)
        attempt = complete_pretest_attempt(
            user_id=str(user_id),
            textbook_id=str(textbook_id),
            chapter_id=str(chapter_id),
            pretest_id=str(pretest.get("id")),
            score=score,
            total_questions=len(questions),
            responses=responses,
            draft_answers=answers,
        )

        return jsonify({
            "status": "success",
            "chapter_id": chapter_id,
            "chapter_title": chapter.get("title"),
            "quiz_unlocked": True,
            "attempt": serialize_pretest_attempt(attempt),
        }), 201


    @app.get("/api/textbooks/<textbook_id>/dashboard")
    @jwt_required()
    def get_textbook_dashboard(textbook_id):
        user_id = get_jwt_identity()

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        recent_limit = request.args.get("recent_limit", default=8, type=int) or 8
        snapshot = get_textbook_dashboard_snapshot(
            user_id, textbook_id, recent_limit=recent_limit
        )
        if not snapshot:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        return jsonify(snapshot), 200


    @app.post("/api/quiz-attempts")
    @jwt_required()
    def post_quiz_attempt():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        quiz_id = data.get("quiz_id")
        answers = data.get("answers")
        score = data.get("score")
        total_questions = data.get("total_questions")
        time_studied = data.get("time_studied", 0)

        if not quiz_id:
            return jsonify({"error": "quiz_id is required"}), 400
        if not isinstance(answers, dict):
            return jsonify({"error": "answers must be a JSON object"}), 400
        try:
            score = int(score)
            total_questions = int(total_questions)
            time_studied = int(time_studied)
        except (TypeError, ValueError):
            return jsonify({"error": "score, total_questions, and time_studied must be integers"}), 400

        if total_questions < 1:
            return jsonify({"error": "total_questions must be at least 1"}), 400
        if score < 0 or score > total_questions:
            return jsonify({"error": "score must be between 0 and total_questions"}), 400
        if time_studied < 0:
            return jsonify({"error": "time_studied must be non-negative"}), 400

        if not quiz_owned_by_user(str(quiz_id), str(user_id)):
            return jsonify({"error": "Quiz not found or unauthorized"}), 404

        try:
            record = submit_quiz_attempt(
                str(user_id),
                str(quiz_id),
                answers,
                score,
                total_questions,
                time_studied,
            )
        except Exception as e:
            return jsonify({"error": "Failed to save attempt", "details": str(e)}), 500

        return jsonify({"status": "success", "attempt": record}), 201


    @app.post("/api/flashcard-sessions")
    @jwt_required()
    def post_flashcard_session():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        flashcard_set_id = data.get("flashcard_set_id")
        time_studied = data.get("time_studied", 0)

        if not flashcard_set_id:
            return jsonify({"error": "flashcard_set_id is required"}), 400
        try:
            time_studied = int(time_studied)
        except (TypeError, ValueError):
            return jsonify({"error": "time_studied must be an integer"}), 400
        if time_studied < 0:
            return jsonify({"error": "time_studied must be non-negative"}), 400

        if not flashcard_set_owned_by_user(str(flashcard_set_id), str(user_id)):
            return jsonify({"error": "Flashcard set not found or unauthorized"}), 404

        try:
            record = store_flashcard_session(str(user_id), str(flashcard_set_id), time_studied)
        except Exception as e:
            return jsonify({"error": "Failed to save session", "details": str(e)}), 500

        return jsonify({"status": "success", "session": record}), 201


    @app.post("/api/summary-sessions")
    @jwt_required()
    def post_summary_session():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        summary_id = data.get("summary_id")
        time_studied = data.get("time_studied", 0)

        if not summary_id:
            return jsonify({"error": "summary_id is required"}), 400
        try:
            time_studied = int(time_studied)
        except (TypeError, ValueError):
            return jsonify({"error": "time_studied must be an integer"}), 400
        if time_studied < 0:
            return jsonify({"error": "time_studied must be non-negative"}), 400

        if not summary_owned_by_user(str(summary_id), str(user_id)):
            return jsonify({"error": "Summary not found or unauthorized"}), 404

        try:
            record = store_summary_session(str(user_id), str(summary_id), time_studied)
        except Exception as e:
            return jsonify({"error": "Failed to save session", "details": str(e)}), 500

        return jsonify({"status": "success", "session": record}), 201


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
        chapter_id = data.get("chapter_id")

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400
        
        if not chapter_id:
            return jsonify({"error": "chapter_id required"}), 400

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        rows, matched_chapter = build_chapter_scoped_rows(
            textbook_id=textbook_id,
            chapter_title=chapter_title,
            user_id=user_id
        )
        if not rows:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        context = build_study_context_from_chunks(rows, max_chars=16000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.generate_summary(context=context, temp=0.3)

        summary_title = f"{chapter_title} Summary"
        summary = create_summary(
            user_id,
            textbook_id,
            chapter_id,
            summary_title,
            result.get("summary") or ""
        )

        return jsonify({
            "status": "success",
            "textbook_id": textbook_id,
            "chapter_title": chapter_title,
            "matched_chapter": matched_chapter,
            "chapter_id": chapter_id,
            "summary_id": summary["id"],
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
        chapter_id = data.get("chapter_id")
        num_cards = int(data.get("num_cards") or 5)

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400
        
        if not chapter_id:
            return jsonify({"error": "chapter_id required"}), 400

        if num_cards < 1 or num_cards > 15:
            return jsonify({"error": "num_cards must be between 1 and 15"}), 400

        owned = get_textbook(user_id, textbook_id)
        if not owned.data:
            return jsonify({"error": "Textbook not found or unauthorized"}), 404

        rows, matched_chapter = build_chapter_scoped_rows(
            textbook_id=textbook_id,
            chapter_title=chapter_title,
            user_id=user_id
        )

        if not rows:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        context = build_study_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        result = llm.generate_flashcards(
            context=context,
            num_cards=num_cards,
            temp=0.3
        )

        flashcards = result.get("flashcards") or []
        if not isinstance(flashcards, list):
            flashcards = []

        set_title = f"{chapter_title} Flashcards"
        flashcard_set = create_flashcard_set(user_id, set_title, textbook_id, chapter_id)

        added_cards = []
        for card in flashcards:
            added_cards.append(
                add_flashcard(
                    flashcard_set["id"], 
                    card["front"], 
                    card["back"], 
                    card["citation"],
            ))

        if not added_cards:
            return jsonify({"error": "No flashcards were generated."}), 500

        return jsonify({
            "status": "success",
            "textbook_id": textbook_id,
            "chapter_title": chapter_title,
            "matched_chapter": matched_chapter,
            "flashcard_set_id": flashcard_set["id"],
            "flashcards": result.get("flashcards") or []
        }), 201

    @app.post("/api/generate/quiz")
    @jwt_required()
    def generate_quiz():
        user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}

        textbook_id = data.get("textbook_id")
        chapter_title = (data.get("chapter_title") or "").strip()
        chapter_id = data.get("chapter_id")
        difficulty = str(data.get("difficulty") or "1")
        num_questions = int(data.get("num_questions") or 5)

        if not textbook_id:
            return jsonify({"error": "textbook_id required"}), 400

        if not chapter_title:
            return jsonify({"error": "chapter_title required"}), 400

        if not chapter_id:
            return jsonify({"error": "chapter_id required"}), 400

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

        rows, matched_chapter = build_chapter_scoped_rows(
            textbook_id=textbook_id,
            chapter_title=chapter_title,
            user_id=user_id
        )

        if not rows:
            return jsonify({"error": "No chunks found for that chapter"}), 400

        context = build_study_context_from_chunks(rows, max_chars=14000)
        if not context.strip():
            return jsonify({"error": "Empty context after filtering"}), 400

        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)

        result = llm.generate_quiz(
            context=context,
            question_type=question_type,
            num_questions=num_questions,
            temp=0.3
        )

        questions = result.get("questions") or []
        if not isinstance(questions, list):
            questions = []

        quiz_title = f"{chapter_title}: {question_type.capitalize()} Quiz"
        quiz = create_quiz(user_id, quiz_title, textbook_id, chapter_id)

        created_questions = []
        for question in questions:
            created_questions.append(
                add_quiz_question(
                    quiz["id"],
                    question["question"],
                    question_type,
                    question["choices"],
                    question["correct_answer"],
                    question["explanation"],
                    question["citation"]
                )
            )

        if not created_questions:
            return jsonify({"error": "No quiz questions were generated."}), 500

        return jsonify({
            "status": "success",
            "textbook_id": textbook_id,
            "chapter_title": chapter_title,
            "matched_chapter": matched_chapter,
            "difficulty": difficulty,
            "question_type": question_type,
            "quiz_id": quiz["id"],
            "questions": result.get("questions") or []
        }), 201
