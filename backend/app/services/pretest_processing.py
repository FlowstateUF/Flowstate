import traceback
from app.services.llm_service import LLMService
from app.services.supabase_service import (
    check_pretest_exists,
    store_pretest
)
from app.services.vector_service import (
    fetch_all_chunks
)
from celery import shared_task
from app.config import settings


# Gets all the chunks for a chapter in page order. If the total exceeds the max character limit, the shortest chunks are dropped first
def build_pretest_context(textbook_id, chapter, user_id, max_chars=100000):

    chapter_title = chapter["title"]
    chapter_start = chapter["start_page"]

    all_results = fetch_all_chunks(textbook_id, chapter_title, user_id)
    if not all_results:
        return ""

    hits = sorted(all_results, key=lambda p: p.payload.get("page_start") or 0)

    snippets = []
    for hit in hits:
        text = (hit.payload.get("text") or "").strip()
        page_start = hit.payload.get("page_start") or 0

        # Not in the chapter
        if page_start < chapter["start_page"] or page_start > chapter["end_page"]:  
            continue

        citation = hit.payload.get("citation", "")
        if not text:
            continue
        snippet = f"{citation}: {text}" if citation else text
        snippets.append(snippet)

    total_chars = sum(len(s) for s in snippets)
    print(f"[context] '{chapter_title}': {len(snippets)} chunks, {total_chars} chars")

    # Best case: eentire chapter fits in context window
    if total_chars <= max_chars:
        return "\n\n".join(snippets)

    # Otherwise drop shortest chunks first, preserving page order for the rest
    indexed = sorted(enumerate(snippets), key=lambda x: len(x[1]))
    total = total_chars
    excluded = set()
    for i, snippet in indexed:
        if total <= max_chars:
            break
        excluded.add(i)
        total -= len(snippet)

    print(f"[context] '{chapter_title}': dropped {len(excluded)} short chunks to fit within {max_chars} chars")
    return "\n\n".join(s for i, s in enumerate(snippets) if i not in excluded)


def generate_chapter_pretest(user_id, textbook_id, chapter, llm):
    chapter_id = chapter["id"]
    chapter_title = chapter["title"]

    if check_pretest_exists(textbook_id, chapter_id):
        print(f"[pretest] '{chapter_title}' already exists, skipping")
        return

    print(f"[pretest] building context for '{chapter_title}'")
    context = build_pretest_context(textbook_id, chapter, user_id)
    if not context.strip():
        print(f"[pretest] no context found for '{chapter_title}', skipping")
        return

    print(f"[pretest] generating questions for '{chapter_title}'")
    try:
        questions = llm.generate_pretest(chapter_title, context)
    except Exception as e:
        print(f"[pretest] LLM call failed for '{chapter_title}':", repr(e))
        traceback.print_exc()
        return

    if not questions:
        print(f"[pretest] no questions returned for '{chapter_title}'")
        return

    try:
        store_pretest(textbook_id, chapter_id, chapter_title, questions)
        print(f"[pretest] stored {len(questions)} questions for '{chapter_title}'")
    except Exception as e:
        print(f"[pretest] failed to store for '{chapter_title}':", repr(e))
        traceback.print_exc()


@shared_task
def generate_all_pretests(user_id, textbook_id, toc):
    try:
        print(f"[pretests] starting for {len(toc)} chapters, textbook={textbook_id}")
        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        for chapter in toc:
            generate_chapter_pretest(user_id, textbook_id, chapter, llm)
        print("[pretests] all done")
    except Exception as e:
        print("PRETEST GENERATION FAILED:", repr(e))
        traceback.print_exc()