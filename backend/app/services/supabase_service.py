from app.clients import supabase
from werkzeug.security import generate_password_hash, check_password_hash

# Users #

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
    return supabase.table('users').select('*').eq('id', user_id).execute().data[0]


# Textbooks #

def upload_textbook_to_supabase(user_id: int, file_bytes: bytes, filename: str) -> dict:
    storage_path = f"{user_id}/{filename}"

    supabase.storage.from_('textbooks').upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "application/pdf"}
    )

    record = supabase.table('textbooks').insert({
        "user_id": user_id,
        "title": filename,
        "storage_path": storage_path,
        "file_size": len(file_bytes)
    }).execute()

    return record.data[0]

def download_textbook_from_supabase(storage_path: str) -> bytes:
    response = supabase.storage.from_('textbooks').download(storage_path)
    return response

def get_textbook_info(textbook_id: str) -> dict:
    result = supabase.table("textbooks").select("*").eq("id", textbook_id).single().execute()
    return result.data

def list_user_textbooks(user_id: str) -> list[dict]:
    result = supabase.table("textbooks").select("*").eq("user_id", user_id).execute()
    return result.data

def update_textbook_status(textbook_id: str, status: str, chunk_count: int = None):
    update = {"status": status}
    if chunk_count is not None:
        update["chunk_count"] = chunk_count
    supabase.table("textbooks").update(update).eq("id", textbook_id).execute()

def delete_textbook(textbook_id: str):
    textbook_path = get_textbook_info(textbook_id)["storage_path"]
    supabase.storage.from_("textbooks").remove(textbook_path)
    supabase.table("textbooks").delete().eq("id", textbook_id).execute()


# Chapters #

def store_toc(textbook_id: str, toc: list[dict]):
    """Store extracted chapter list in the chapters table."""
    rows = [
        {
            "textbook_id": textbook_id,
            "title": chapter["title"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"]
        }
        for chapter in toc
    ]
    supabase.table("chapters").insert(rows).execute()

def get_toc(textbook_id: str) -> list[dict]:
    result = supabase.table("chapters").select("*").eq("textbook_id", textbook_id).order("start_page", ascending=True).execute()
    return result.data

