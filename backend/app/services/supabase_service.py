from app.clients import supabase
from werkzeug.security import generate_password_hash, check_password_hash


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

def delete_textbook_for_user(user_id: str, textbook_id: str) -> dict | None:
    info = get_textbook_info(textbook_id)
    if not info or str(info.get("user_id")) != str(user_id):
        return None

    storage_path = info.get("storage_path")

    supabase.table("pretests").delete().eq("textbook_id", textbook_id).execute()
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

def get_textbook_page_count(textbook_id: str) -> int | None:
    res = supabase.table("textbooks").select("page_count").eq("id", textbook_id).single().execute()
    if not res.data:
        return None
    return res.data.get("page_count")

def fetch_chapter_chunks(textbook_id: str, chapter_id: str, limit: int = 60) -> list[dict]:
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
        .single()
        .execute()
    )
    return result.data

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
    if not res.data:
        return []
    return res.data.get("topics") or []