from app.supabase_client import supabase

# Supabase storage upload and download functions

def upload_doc_to_supabase(user_id: int, file_bytes: bytes, filename: str) -> str:
    storage_path = f"{user_id}/{filename}"
    try:
        supabase.storage.from_('docs').upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"}
        )
        return storage_path
    except Exception as e:
        raise Exception(f"Supabase upload failed: {e}")


def download_doc_from_supabase(storage_path: str) -> bytes:
    try:
        response = supabase.storage.from_('docs').download(storage_path)
        return response
    except Exception as e:
        raise Exception(f"Supabase download failed: {e}")
