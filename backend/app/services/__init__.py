from .embedding_service import embed_texts, embed_query
from .supabase_service import (
    create_user, 
    authenticate_user, 
    check_username_exists, 
    check_email_exists, 
    get_user_by_id, 
    upload_textbook_to_supabase, 
    download_textbook_from_supabase,
    get_textbook_info,
    list_user_textbooks,
    update_textbook_status,
    delete_textbook,
    store_toc,
    get_toc
)
from .textbook_service import extract_toc, parse_and_chunk
from .vector_service import upsert_chunks