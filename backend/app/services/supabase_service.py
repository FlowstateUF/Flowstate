from datetime import datetime, timedelta, timezone
from collections import defaultdict

from app.clients import supabase
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone


# Users 

def create_user(username, password, email) -> dict:
    hashed_password = generate_password_hash(password)

    record = supabase.table('users').insert({
        "username": username,
        "password": hashed_password,
        "email": email
    }).execute()

    return record.data[0]

def authenticate_user(email, password) -> dict:
    response = supabase.table('users').select('*').eq('email', email).execute()

    if not response.data:  
        return {"error": "Invalid email or password"}
    
    user = response.data[0]

    if user and check_password_hash(user['password'], password):
        return user
    else:
        return {"error": "Invalid email or password"}
    
def check_username_exists(username) -> bool:
    response = supabase.table('users').select('*').eq('username', username).execute()

    return len(response.data) > 0

def check_email_exists(email) -> bool:
    response = supabase.table('users').select('*').eq('email', email).execute()

    return len(response.data) > 0

def get_user_by_id(user_id) -> dict:
    result = supabase.table('users').select('*').eq('id', user_id).execute()
    if not result.data:
        return {"error": "User not found"}
    return result.data[0]


# Textbooks 

def upload_textbook_to_supabase(user_id: int, file_bytes: bytes, filename: str, file_hash: str) -> dict:
    storage_path = f"{user_id}/{filename}"

    try:
        supabase.storage.from_('textbooks').remove([storage_path])
    except Exception:
        pass

    supabase.storage.from_('textbooks').upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf"}
    )

    record = supabase.table('textbooks').insert({
        "user_id": user_id,
        "title": filename,
        "storage_path": storage_path,
        "file_size": len(file_bytes),
        "status": "processing",
        "file_hash": file_hash
    }).execute()

    return record.data[0]

def download_textbook_from_supabase(storage_path: str) -> bytes:
    response = supabase.storage.from_('textbooks').download(storage_path)
    return response

def get_textbook_info(textbook_id: str) -> dict:
    result = supabase.table("textbooks").select("*").eq("id", textbook_id).single().execute()
    return result.data

def list_user_textbooks(user_id: str, include_all: bool = False) -> list[dict]:
    query = supabase.table("textbooks").select("*").eq("user_id", user_id)

    if not include_all:
        query = query.eq("is_starred", True)

    result = query.execute()
    return result.data or []

def update_textbook_status(textbook_id: str, status: str, chunk_count: int = None):
    update = {"status": status}
    if chunk_count is not None:
        update["chunk_count"] = chunk_count
    supabase.table("textbooks").update(update).eq("id", textbook_id).execute()

def delete_textbook(textbook_id: str):
    textbook_path = get_textbook_info(textbook_id)["storage_path"]
    supabase.storage.from_("textbooks").remove(textbook_path)
    supabase.table("textbooks").delete().eq("id", textbook_id).execute()

def get_textbook(user_id: str, textbook_id: str):
    res = (
        supabase.table("textbooks")
        .select("id")
        .eq("id", textbook_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return res

def rename_textbook_for_user(user_id: str, textbook_id: str, new_title: str) -> dict | None:
    result = (
        supabase.table("textbooks")
        .update({"title": new_title})
        .eq("id", textbook_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None

def set_textbook_starred_for_user(user_id: str, textbook_id: str, is_starred: bool) -> dict | None:
    result = (
        supabase.table("textbooks")
        .update({"is_starred": is_starred})
        .eq("id", textbook_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None

# Gets the child record ids we need so delete cleanup stays targeted.
def get_textbook_child_record_ids(textbook_id: str) -> dict[str, list[str]]:
    quiz_rows = (
        supabase.table("quizzes")
        .select("id")
        .eq("textbook_id", textbook_id)
        .execute()
    ).data or []

    flashcard_set_rows = (
        supabase.table("flashcard_sets")
        .select("id")
        .eq("textbook_id", textbook_id)
        .execute()
    ).data or []

    summary_rows = (
        supabase.table("summaries")
        .select("id")
        .eq("textbook_id", textbook_id)
        .execute()
    ).data or []

    return {
        "quiz_ids": [str(row.get("id")) for row in quiz_rows if row.get("id")],
        "flashcard_set_ids": [str(row.get("id")) for row in flashcard_set_rows if row.get("id")],
        "summary_ids": [str(row.get("id")) for row in summary_rows if row.get("id")],
    }

# Deletes rows by id list without blowing up on empty lists.
def delete_rows_by_ids(table_name: str, column_name: str, ids: list[str]):
    if not ids:
        return
    supabase.table(table_name).delete().in_(column_name, ids).execute()

def delete_textbook_for_user(user_id: str, textbook_id: str) -> dict | None:
    info = get_textbook_info(textbook_id)
    if not info or str(info.get("user_id")) != str(user_id):
        return None

    storage_path = info.get("storage_path")
    child_ids = get_textbook_child_record_ids(textbook_id)
    quiz_ids = child_ids.get("quiz_ids") or []
    flashcard_set_ids = child_ids.get("flashcard_set_ids") or []
    summary_ids = child_ids.get("summary_ids") or []

    try:
        supabase.table("pretest_attempts").delete().eq("textbook_id", textbook_id).execute()
    except Exception:
        pass

    delete_rows_by_ids("quiz_attempts", "quiz_id", quiz_ids)
    delete_rows_by_ids("quiz_questions", "quiz_id", quiz_ids)
    delete_rows_by_ids("flashcard_sessions", "flashcard_set_id", flashcard_set_ids)
    delete_rows_by_ids("flashcards", "flashcard_set_id", flashcard_set_ids)
    delete_rows_by_ids("summary_sessions", "summary_id", summary_ids)

    supabase.table("pretests").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("quizzes").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("flashcard_sets").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("summaries").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("chunks").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("chapters").delete().eq("textbook_id", textbook_id).execute()
    supabase.table("textbooks").delete().eq("id", textbook_id).eq("user_id", user_id).execute()

    if storage_path:
        try:
            supabase.storage.from_("textbooks").remove([storage_path])
        except Exception:
            pass

    return info

def check_textbook_exists(user_id: str, file_hash: str):
    res = (
        supabase.table("textbooks")
        .select("id, status, title")
        .eq("user_id", user_id)
        .eq("file_hash", file_hash)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


# Chapters 

def store_toc(textbook_id: str, toc: list[dict], total_pages: int):
    """Store page_count in textbooks table and extracted chapter list in the chapters table."""
    rows = [
        {
            "textbook_id": textbook_id,
            "title": chapter["title"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"]
        }
        for chapter in toc
    ]
    supabase.table("textbooks").update({"page_count": total_pages}).eq("id", textbook_id).execute()
    supabase.table("chapters").insert(rows).execute()

def get_toc(textbook_id: str) -> list[dict]:
    result = supabase.table("chapters").select("*").eq("textbook_id", textbook_id).order("start_page").execute()
    return result.data

def get_chapter(textbook_id: str, chapter_id: str) -> dict | None:
    result = (
        supabase.table("chapters")
        .select("*")
        .eq("textbook_id", textbook_id)
        .eq("id", chapter_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None

def get_textbook_page_count(textbook_id: str) -> int | None:
    res = supabase.table("textbooks").select("page_count").eq("id", textbook_id).single().execute()
    if not res.data:
        return None
    return res.data.get("page_count")

def fetch_chapter_chunks(textbook_id: str, chapter_id: str, limit: int = 60) -> list[dict]:
    # Pull the first N chunks in that chapter (ordered)
    res = (
        supabase.table("chunks")
        .select("id, page_number, index, content")
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .order("page_number")
        .order("index")
        .limit(limit)
        .execute()
    )
    return res.data or []


# Pretests 

def store_pretest(textbook_id: str, chapter_id: str, chapter_title: str, questions: list[dict]):
    supabase.table("pretests").insert({
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "questions": questions,
        "status": "ready",
    }).execute()

def get_pretest(textbook_id: str, chapter_id: str) -> dict | None:
    result = (
        supabase.table("pretests")
        .select("*")
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None

def check_pretest_exists(textbook_id: str, chapter_id: str) -> bool:
    res = (
        supabase.table("pretests")
        .select("id")
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)

def get_pretest_attempt(user_id: str, textbook_id: str, chapter_id: str) -> dict | None:
    result = (
        supabase.table("pretest_attempts")
        .select("*")
        .eq("user_id", user_id)
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None

def save_pretest_attempt_progress(
    user_id: str,
    textbook_id: str,
    chapter_id: str,
    pretest_id: str,
    total_questions: int,
    draft_answers: list,
    current_question_index: int,
) -> dict:
    existing = get_pretest_attempt(user_id, textbook_id, chapter_id)

    payload = {
        "user_id": user_id,
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "pretest_id": pretest_id,
        "status": "in_progress",
        "total_questions": total_questions,
        "draft_answers": draft_answers,
        "current_question_index": current_question_index,
    }

    if existing:
        result = (
            supabase.table("pretest_attempts")
            .update(payload)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = supabase.table("pretest_attempts").insert(payload).execute()

    return result.data[0]

def complete_pretest_attempt(
    user_id: str,
    textbook_id: str,
    chapter_id: str,
    pretest_id: str,
    score: int,
    total_questions: int,
    responses: list[dict],
    draft_answers: list,
) -> dict:
    existing = get_pretest_attempt(user_id, textbook_id, chapter_id)
    payload = {
        "user_id": user_id,
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "pretest_id": pretest_id,
        "status": "completed",
        "score": score,
        "total_questions": total_questions,
        "responses": responses,
        "draft_answers": draft_answers,
        "current_question_index": max(total_questions - 1, 0),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    if existing:
        result = (
            supabase.table("pretest_attempts")
            .update(payload)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = supabase.table("pretest_attempts").insert(payload).execute()

    return result.data[0]

# Chapter Topics

def store_chapter_topics(chapter_id: str, topics: list[str]):
    supabase.table("chapters").update({
        "topics": topics
    }).eq("id", chapter_id).execute()


def get_chapter_topics(chapter_id: str) -> list[str]:
    res = (
        supabase.table("chapters")
        .select("topics")
        .eq("id", chapter_id)
        .single()
        .execute()
    )
    return res.data.get("topics") if res.data else []

# Flashcards

def create_flashcard_set(user_id: str, title: str, textbook_id: str = None, chapter_id: str = None) -> dict:
    record = supabase.table("flashcard_sets").insert({
        "user_id": user_id,
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "title": title
    }).execute()
    return record.data[0]

def add_flashcard(flashcard_set_id: str, front: str, back: str, citation: str,) -> dict:
    record = supabase.table("flashcards").insert({
        "flashcard_set_id": flashcard_set_id,
        "front": front,
        "back": back,
        "citation": citation,
    }).execute()
    return record.data[0]

def get_flashcard_set(flashcard_set_id: str) -> dict:
    res = (
        supabase.table("flashcard_sets")
        .select("*, flashcards(*)")
        .eq("id", flashcard_set_id)
        .single()
        .execute()
    )
    return res.data

def store_flashcard_session(user_id: str, flashcard_set_id: str, time_studied: int) -> dict:
    record = supabase.table("flashcard_sessions").insert({
        "user_id": user_id,
        "flashcard_set_id": flashcard_set_id,
        "time_studied": time_studied
    }).execute()

    old_time_studied = (
        supabase.table("flashcard_sets")
        .select("time_studied")
        .eq("id", flashcard_set_id)
        .single()
        .execute()
    ).data.get("time_studied")

    supabase.table("flashcard_sets").update({"time_studied": old_time_studied + time_studied}).eq("id", flashcard_set_id).execute()

    return record.data[0]

def get_user_flashcard_history(user_id: str) -> list[dict]:
    res = (
        supabase.table("flashcard_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("studied_at", desc=True)
        .execute()
    )
    return res.data or []

def flashcard_set_owned_by_user(flashcard_set_id: str, user_id: str) -> bool:
    r = (
        supabase.table("flashcard_sets")
        .select("id")
        .eq("id", flashcard_set_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(r.data)

# Quizzes

def create_quiz(user_id: str, title: str, textbook_id: str, chapter_id: str) -> dict:
    record = supabase.table("quizzes").insert({
        "user_id": user_id,
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "title": title
    }).execute()
    return record.data[0]

def add_quiz_question(quiz_id: str, question: str, question_type: str, choices: dict, answer: str, explanation: str, citation: str, topic: str = None) -> dict:
    record = supabase.table("quiz_questions").insert({
        "quiz_id": quiz_id,
        "question": question,
        "difficulty_type": question_type,
        "choices": choices,
        "answer": answer,
        "explanation": explanation,
        "citation": citation,
        "topic": topic if topic else ""
    }).execute()
    return record.data[0]

def get_quiz(quiz_id: str) -> dict:
    res = (
        supabase.table("quizzes")
        .select("*, quiz_questions(*)")
        .eq("id", quiz_id)
        .single()
        .execute()
    )
    return res.data

def quiz_owned_by_user(quiz_id: str, user_id: str) -> bool:
    r = (
        supabase.table("quizzes")
        .select("id")
        .eq("id", quiz_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(r.data)

def submit_quiz_attempt(user_id: str, quiz_id: str, answers: dict, score: int, total_questions: int, time_studied: int) -> dict:
    record = supabase.table("quiz_attempts").insert({
        "user_id": user_id,
        "quiz_id": quiz_id,
        "answers": answers,
        "score": score,
        "total_questions": total_questions,
        "time_studied": time_studied
    }).execute()

    old_time_studied = (
        supabase.table("quizzes")
        .select("time_studied")
        .eq("id", quiz_id)
        .single()
        .execute()
    ).data.get("time_studied")

    supabase.table("quizzes").update({"time_studied": old_time_studied + time_studied}).eq("id", quiz_id).execute()

    return record.data[0]

def get_user_quiz_history(user_id: str) -> list[dict]:
    res = (
        supabase.table("quiz_attempts")
        .select("*")
        .eq("user_id", user_id)
        .order("completed_at", desc=True)
        .execute()
    )
    return res.data or []

# Summaries

def create_summary(user_id: str, textbook_id: str, chapter_id: str, title: str, content: dict) -> dict:
    record = supabase.table("summaries").insert({
        "user_id": user_id,
        "textbook_id": textbook_id,
        "chapter_id": chapter_id,
        "title": title,
        "content": content
    }).execute()
    return record.data[0]

def store_summary_session(user_id: str, summary_id: str, time_studied: int) -> dict:
    record = supabase.table("summary_sessions").insert({
        "user_id": user_id,
        "summary_id": summary_id,
        "time_studied": time_studied
    }).execute()

    old_time_studied = (
        supabase.table("summaries")
        .select("time_studied")
        .eq("id", summary_id)
        .single()
        .execute()
    ).data.get("time_studied")

    supabase.table("summaries").update({"time_studied": old_time_studied + time_studied}).eq("id", summary_id).execute()

    return record.data[0]

def get_user_summary_history(user_id: str) -> list[dict]:
    res = (
        supabase.table("summary_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("studied_at", desc=True)
        .execute()
    )
    return res.data or []

def summary_owned_by_user(summary_id: str, user_id: str) -> bool:
    r = (
        supabase.table("summaries")
        .select("id")
        .eq("id", summary_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return bool(r.data)


# Dashboard (might move later)

# Parses a stored timestamp into a timezone-aware datetime.
def parse_timestamp(ts) -> datetime | None:
    if not ts:
        return None
    s = str(ts).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# Finds which recent-day bucket a timestamp belongs to.
def get_day_index(dt: datetime | None, day_keys: list) -> int | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    current_day = dt.astimezone(timezone.utc).date()
    for index, day_key in enumerate(day_keys):
        if current_day == day_key:
            return index
    return None


# Adds one activity event into the right daily bucket.
def bump_day_bucket(day_bucket: dict[str, dict[str, int]], dt_raw, kind_key: str):
    dt = parse_timestamp(dt_raw)
    if not dt:
        return
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    day_key = dt.astimezone(timezone.utc).date().isoformat()
    day_bucket[day_key][kind_key] += 1
    day_bucket[day_key]["total"] += 1


def confidence_label_to_percent(label) -> float | None:
    normalized = str(label or "").strip().lower()
    lookup = {
        "low": 0.25,
        "medium": 0.70,
        "high": 1.00,
    }
    return lookup.get(normalized)


def classify_confidence_gap(confidence_ratio: float, actual_ratio: float) -> str:
    confidence = max(0.0, min(1.0, float(confidence_ratio or 0)))
    actual = max(0.0, min(1.0, float(actual_ratio or 0)))
    gap_points = round((confidence - actual) * 100)

    if abs(gap_points) <= 20:
        return "accurate"
    if gap_points > 0:
        return "overconfidence"
    return "underconfidence"


def build_confidence_gap_point(
    *,
    kind: str,
    title: str,
    attempt_id: str | None,
    quiz_id: str | None,
    chapter_id: str | None,
    chapter_title: str | None,
    completed_at,
    question_points: list[tuple[float, float]],
) -> dict | None:
    if not question_points:
        return None

    confidence_percent = sum(confidence for confidence, _ in question_points) / len(question_points)
    actual_percent = sum(actual for _, actual in question_points) / len(question_points)
    actual = max(0.0, min(1.0, float(actual_percent or 0)))
    confidence = max(0.0, min(1.0, float(confidence_percent)))
    gap = round((confidence - actual) * 100)

    return {
        "kind": kind,
        "title": title,
        "attempt_id": attempt_id,
        "quiz_id": quiz_id,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "completed_at": completed_at,
        "confidence_percent": round(confidence * 100),
        "actual_percent": round(actual * 100),
        "confidence_ratio": round(confidence, 4),
        "actual_ratio": round(actual, 4),
        "category": classify_confidence_gap(confidence, actual),
        "gap_points": gap,
        "mismatch_ratio": round(abs(confidence - actual), 4),
    }

def get_textbook_dashboard_snapshot(
    user_id: str, textbook_id: str, recent_limit: int = 8
) -> dict | None:
    """Aggregate study activity, per-chapter quiz mastery, and recent sessions for one textbook."""
    info = get_textbook_info(textbook_id)
    if not info or str(info.get("user_id")) != str(user_id):
        return None

    chapters = get_toc(textbook_id) or []
    chapter_titles = {str(c["id"]): (c.get("title") or "Chapter") for c in chapters}

    fc_sets = (
        supabase.table("flashcard_sets")
        .select("id, title, chapter_id")
        .eq("textbook_id", textbook_id)
        .eq("user_id", user_id)
        .execute()
    ).data or []
    fc_set_ids = [r["id"] for r in fc_sets]
    fc_title_by_set = {r["id"]: r.get("title") or "Flashcards" for r in fc_sets}

    flash_sessions: list[dict] = []
    if fc_set_ids:
        flash_sessions = (
            supabase.table("flashcard_sessions")
            .select("*")
            .eq("user_id", user_id)
            .in_("flashcard_set_id", fc_set_ids)
            .execute()
        ).data or []

    quiz_rows = (
        supabase.table("quizzes")
        .select("id, title, chapter_id")
        .eq("textbook_id", textbook_id)
        .eq("user_id", user_id)
        .execute()
    ).data or []
    quiz_ids = [r["id"] for r in quiz_rows]
    quiz_chapter = {str(r["id"]): str(r.get("chapter_id") or "") for r in quiz_rows}
    quiz_titles = {str(r["id"]): (r.get("title") or "Quiz") for r in quiz_rows}
    quiz_answer_keys: dict[str, list[str]] = defaultdict(list)

    if quiz_ids:
        quiz_question_rows = (
            supabase.table("quiz_questions")
            .select("quiz_id, answer, created_at")
            .in_("quiz_id", quiz_ids)
            .order("created_at")
            .execute()
        ).data or []

        for row in quiz_question_rows:
            quiz_answer_keys[str(row.get("quiz_id") or "")].append(
                str(row.get("answer") or "").strip().upper()
            )

    quiz_attempts: list[dict] = []
    if quiz_ids:
        quiz_attempts = (
            supabase.table("quiz_attempts")
            .select("*")
            .eq("user_id", user_id)
            .in_("quiz_id", quiz_ids)
            .execute()
        ).data or []

    summ_rows = (
        supabase.table("summaries")
        .select("id, title, chapter_id")
        .eq("textbook_id", textbook_id)
        .eq("user_id", user_id)
        .execute()
    ).data or []
    summary_ids = [r["id"] for r in summ_rows]
    summary_titles = {str(r["id"]): (r.get("title") or "Summary") for r in summ_rows}

    summary_sessions_list: list[dict] = []
    if summary_ids:
        summary_sessions_list = (
            supabase.table("summary_sessions")
            .select("*")
            .eq("user_id", user_id)
            .in_("summary_id", summary_ids)
            .execute()
        ).data or []

    pretest_attempts = (
        supabase.table("pretest_attempts")
        .select("*")
        .eq("user_id", user_id)
        .eq("textbook_id", textbook_id)
        .eq("status", "completed")
        .execute()
    ).data or []

    # --- Activity: last 7 days, session counts per type
    today = datetime.now(timezone.utc).date()
    day_keys = [today - timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%a") for d in day_keys]

    counts_quiz = [0] * 7
    counts_fc = [0] * 7
    counts_sum = [0] * 7

    for row in quiz_attempts:
        dt = parse_timestamp(row.get("completed_at"))
        idx = get_day_index(dt, day_keys)
        if idx is not None:
            counts_quiz[idx] += 1

    for row in flash_sessions:
        dt = parse_timestamp(row.get("studied_at"))
        idx = get_day_index(dt, day_keys)
        if idx is not None:
            counts_fc[idx] += 1

    for row in summary_sessions_list:
        dt = parse_timestamp(row.get("studied_at"))
        idx = get_day_index(dt, day_keys)
        if idx is not None:
            counts_sum[idx] += 1

    session_count_last_7 = sum(counts_quiz) + sum(counts_fc) + sum(counts_sum)
    active_days_last_7 = sum(
        1
        for i in range(7)
        if counts_quiz[i] + counts_fc[i] + counts_sum[i] > 0
    )

    # --- Mastery: average quiz score % per chapter
    best_by_quiz: dict[str, float] = {}
    for row in quiz_attempts:
        qid = str(row.get("quiz_id") or "")
        score = row.get("score")
        total = row.get("total_questions")
        if not qid or total is None or int(total) <= 0:
            continue
        pct = 100.0 * float(score or 0) / float(total)
        if qid not in best_by_quiz or pct > best_by_quiz[qid]:
            best_by_quiz[qid] = pct

    chapter_scores: defaultdict[str, list[float]] = defaultdict(list)
    for qid, pct in best_by_quiz.items():
        ch = quiz_chapter.get(qid)
        if ch:
            chapter_scores[ch].append(pct)

    mastery_chapters = []
    for cid, title in chapter_titles.items():
        scores = chapter_scores.get(cid, [])
        avg = round(sum(scores) / len(scores)) if scores else 0
        mastery_chapters.append(
            {"chapter_id": cid, "title": title, "quiz_mastery_percent": avg, "quizzes_with_attempts": len(scores)}
        )
    mastery_chapters.sort(key=lambda x: (x["quiz_mastery_percent"], x["title"]), reverse=True)

    overall = 0
    if best_by_quiz:
        overall = round(sum(best_by_quiz.values()) / len(best_by_quiz))

    confidence_gap_points: list[dict] = []
    for row in quiz_attempts:
        answers = row.get("answers") or {}
        if not isinstance(answers, dict):
            continue

        question_points = []
        answer_key_list = quiz_answer_keys.get(str(row.get("quiz_id") or ""), [])
        ordered_answers = sorted(
            answers.items(),
            key=lambda item: int(item[0]) if str(item[0]).isdigit() else 9999,
        )
        for index, (_, value) in enumerate(ordered_answers):
            if not isinstance(value, dict):
                continue
            confidence_value = confidence_label_to_percent(value.get("confidence"))
            selected_answer = str(value.get("answer") or "").strip().upper()
            correct_answer = answer_key_list[index] if index < len(answer_key_list) else ""
            actual_value = 1.0 if selected_answer and selected_answer == correct_answer else 0.0
            if confidence_value is not None:
                question_points.append((confidence_value, actual_value))

        point = build_confidence_gap_point(
            kind="quiz",
            title=quiz_titles.get(str(row.get("quiz_id") or ""), "Quiz"),
            attempt_id=str(row.get("id") or ""),
            quiz_id=str(row.get("quiz_id") or ""),
            chapter_id=quiz_chapter.get(str(row.get("quiz_id") or ""), ""),
            chapter_title=chapter_titles.get(quiz_chapter.get(str(row.get("quiz_id") or ""), ""), "Chapter"),
            completed_at=row.get("completed_at"),
            question_points=question_points,
        )
        if point:
            confidence_gap_points.append(point)

    confidence_gap_points.sort(
        key=lambda point: parse_timestamp(point.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    confidence_gap_summary = {
        "accurate": sum(
            1
            for point in confidence_gap_points
            if point["category"] == "accurate"
        ),
        "overconfidence": sum(
            1
            for point in confidence_gap_points
            if point["category"] == "overconfidence"
        ),
        "underconfidence": sum(
            1
            for point in confidence_gap_points
            if point["category"] == "underconfidence"
        ),
    }

    # --- Recent sessions (unified, max 8)
    unified: list[dict] = []

    for row in quiz_attempts:
        qid = str(row.get("quiz_id") or "")
        dt = parse_timestamp(row.get("completed_at"))
        score = row.get("score")
        total = row.get("total_questions")
        pct_s = ""
        if total is not None and int(total) > 0:
            pct_s = f"{round(100 * float(score or 0) / float(total))}%"
        unified.append(
            {
                "kind": "quiz",
                "title": quiz_titles.get(qid, "Quiz"),
                "at": row.get("completed_at"),
                "sort_at": dt,
                "duration_seconds": int(row.get("time_studied") or 0),
                "detail": pct_s,
            }
        )

    for row in flash_sessions:
        sid = row.get("flashcard_set_id")
        sid_s = str(sid) if sid else ""
        dt = parse_timestamp(row.get("studied_at"))
        unified.append(
            {
                "kind": "flashcards",
                "title": fc_title_by_set.get(sid_s, "Flashcards"),
                "at": row.get("studied_at"),
                "sort_at": dt,
                "duration_seconds": int(row.get("time_studied") or 0),
                "detail": "",
            }
        )

    for row in summary_sessions_list:
        sid = str(row.get("summary_id") or "")
        dt = parse_timestamp(row.get("studied_at"))
        unified.append(
            {
                "kind": "summary",
                "title": summary_titles.get(sid, "Summary"),
                "at": row.get("studied_at"),
                "sort_at": dt,
                "duration_seconds": int(row.get("time_studied") or 0),
                "detail": "",
            }
        )

    unified.sort(key=lambda x: x["sort_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    recent = []
    cap = max(1, min(int(recent_limit or 8), 200))
    for u in unified[:cap]:
        recent.append(
            {
                "kind": u["kind"],
                "title": u["title"],
                "at": u["at"],
                "duration_seconds": u["duration_seconds"],
                "detail": u["detail"],
            }
        )

    # --- Average quiz mastery across all TOC chapters
    n_chapters = len(mastery_chapters)
    avg_chapter_mastery_percent = (
        round(sum(c["quiz_mastery_percent"] for c in mastery_chapters) / n_chapters)
        if n_chapters
        else 0
    )

    total_study_seconds = sum(
        int(row.get("time_studied") or 0)
        for row in quiz_attempts + flash_sessions + summary_sessions_list
    )

    # --- Per-day counts for heatmap + streaks
    day_bucket: dict[str, dict[str, int]] = defaultdict(
        lambda: {"quiz": 0, "flashcards": 0, "summaries": 0, "total": 0}
    )

    for row in quiz_attempts:
        bump_day_bucket(day_bucket, row.get("completed_at"), "quiz")
    for row in flash_sessions:
        bump_day_bucket(day_bucket, row.get("studied_at"), "flashcards")
    for row in summary_sessions_list:
        bump_day_bucket(day_bucket, row.get("studied_at"), "summaries")

    active_dates = {d for d, v in day_bucket.items() if v["total"] > 0}

    # Current streak
    streak_current = 0
    d_cursor = today
    while d_cursor.isoformat() in active_dates:
        streak_current += 1
        d_cursor -= timedelta(days=1)

    # Longest streak
    streak_longest = 0
    if active_dates:
        sorted_days = sorted(datetime.fromisoformat(x).date() for x in active_dates)
        run = 1
        streak_longest = 1
        for i in range(1, len(sorted_days)):
            if sorted_days[i] - sorted_days[i - 1] == timedelta(days=1):
                run += 1
                streak_longest = max(streak_longest, run)
            else:
                run = 1

    # Heatmap: last 371 days
    heatmap_start = today - timedelta(days=370)
    heatmap_days = []
    walk = heatmap_start
    while walk <= today:
        key = walk.isoformat()
        b = day_bucket.get(
            key, {"quiz": 0, "flashcards": 0, "summaries": 0, "total": 0}
        )
        heatmap_days.append(
            {
                "date": key,
                "quiz": b["quiz"],
                "flashcards": b["flashcards"],
                "summaries": b["summaries"],
                "total": b["total"],
            }
        )
        walk += timedelta(days=1)

    # Strength / weakness by chapter mastery
    attempted = [c for c in mastery_chapters if c["quizzes_with_attempts"] > 0]
    weakest = None
    strongest = None
    if attempted:
        weakest = min(attempted, key=lambda c: (c["quiz_mastery_percent"], c["title"]))
        strongest = max(attempted, key=lambda c: (c["quiz_mastery_percent"], c["title"]))

    return {
        "textbook_id": textbook_id,
        "activity": {
            "day_labels": day_labels,
            "session_count_last_7": session_count_last_7,
            "active_days_last_7": active_days_last_7,
            "series": [
                {"key": "quiz", "label": "Quiz", "values": counts_quiz},
                {"key": "flashcards", "label": "Flashcards", "values": counts_fc},
                {"key": "summaries", "label": "Summaries", "values": counts_sum},
            ],
        },
        "mastery": {
            "overall_quiz_percent": overall,
            "avg_chapter_mastery_percent": avg_chapter_mastery_percent,
            "chapter_count": n_chapters,
            "chapters": mastery_chapters,
            "strongest_chapter": strongest,
            "weakest_chapter": weakest,
        },
        "study": {
            "total_study_seconds": total_study_seconds,
            "streak_current_days": streak_current,
            "streak_longest_days": streak_longest,
            "total_session_events": len(quiz_attempts)
            + len(flash_sessions)
            + len(summary_sessions_list),
        },
        "heatmap": {
            "granularity": "day",
            "days": heatmap_days,
        },
        "confidence_gap": {
            "points": confidence_gap_points,
            "summary": confidence_gap_summary,
        },
        "recent_sessions": recent,
    }
