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
    get_toc,
    get_textbook_page_count,
    store_pretest,
    get_pretest
)
from .textbook_service import extract_toc, parse_and_chunk, pdf_page_range
from .vector_service import upsert_chunks
from .llm_service import LLMService
from .question_prompts import QUESTION_TYPES, MC_BASE_PROMPT, FLASHCARD_PROMPT, SUMMARY_PROMPT, PRETEST_BATCH_PROMPT