from app.clients import supabase
from werkzeug.security import generate_password_hash, check_password_hash


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
        "storage_path": storage_path
    }).execute()

    return record.data[0]

def download_textbook_from_supabase(storage_path: str) -> bytes:
    response = supabase.storage.from_('textbooks').download(storage_path)
    return response


