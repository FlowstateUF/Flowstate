import traceback
import pymupdf
from app.services import (
    get_toc, parse_and_chunk, embed_texts, upsert_chunks,
    update_textbook_status, get_textbook_page_count, pdf_page_range,
    store_pretest, LLMService
)
from app.config import settings
from app.clients import qdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.clients import supabase

def compute_page_coverage(chunks):
    pages = []
    for c in chunks:
        p = c.get("page_start")
        if isinstance(p, int):
            pages.append(p)
            continue
        # fallback if you still have old schema somewhere
        p = c.get("page_number")
        if isinstance(p, int):
            pages.append(p)

    return (min(pages), max(pages), len(set(pages))) if pages else (None, None, 0)

# def process_textbook(user_id: str, textbook_id: str, file_bytes: bytes):
#     """
#     Runs in a background thread immediately after upload.

#     Flow:
#       1. Fetch TOC already stored in Supabase during upload
#       2. Run Docling on the full textbook
#       3. Embed all chunks in batches of 100
#       4. Store chunks & vectors in Qdrant
#       5. Update document status to ready
#     """
#     try:
#         update_textbook_status(textbook_id, "processing")
#         toc = get_toc(textbook_id)

#         chunks = parse_and_chunk(file_bytes, user_id, textbook_id, toc)

#         # Coverage check (BEFORE embeddings so you can detect partial early)
#         total_pages = get_textbook_page_count(textbook_id)  # you need to implement this
#         min_p, max_p, distinct_pages = compute_page_coverage(chunks)

#         # Decide status based on coverage
#         status = "ready"
#         if total_pages and max_p is not None:
#             if max_p < int(0.9 * total_pages):
#                 status = "partial"
#         else:
#             # if we can't compute coverage reliably, be conservative
#             status = "partial"

#         texts = [c["text"] for c in chunks]
#         embeddings = []
#         for i in range(0, len(texts), 100):
#             embeddings.extend(embed_texts(texts[i:i + 100]))

#         upsert_chunks(chunks, embeddings)
#         print("coverage:", {"min": min_p, "max": max_p, "distinct_pages": distinct_pages, "total_pages": total_pages, "status": status})
#         update_textbook_status(textbook_id, status, len(chunks))

#     except Exception as e:
#         update_textbook_status(textbook_id, "failed")
#         print("PROCESS_TEXTBOOK FAILED:", repr(e))
#         traceback.print_exc()
#         raise e

# Function that constructs the context for a pretest
def build_pretest_context(textbook_id, chapter_title, max_chars=30000):

    # Filter to only this chapter's chunks
    flt = Filter(must=[
        FieldCondition(key="textbook_id", match=MatchValue(value=str(textbook_id))),
        FieldCondition(key="chapter", match=MatchValue(value=chapter_title)),
    ])

    all_results = []
    offset = None

    # Fetch all chunks, scrolling sequentially through all chunks
    while True:
        results, offset = qdrant.scroll(
            collection_name="chunks",
            scroll_filter=flt,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        all_results.extend(results)
        if offset is None:
            break

    hits = sorted(all_results, key=lambda p: p.payload.get("page_start") or 0)

    # Build the context string, stop if we hit the char limit
    parts = []
    total = 0
    for hit in hits:
        text = (hit.payload.get("text") or "").strip()
        citation = hit.payload.get("citation", "")
        if not text:
            continue
        snippet = f"{citation}: {text}" if citation else text
        if total + len(snippet) > max_chars:
            break
        parts.append(snippet)
        total += len(snippet)

    return "\n\n".join(parts)


# Goes through every section in TOC and generates pretest if it is stored as a chapter in QDRANT database
# TODO: find a way to only go through chapters, its technically checking every part of the TOC but only generating for actual chapters in QDRANT (as it should), just seems unecesarry to loop through every section (see terminal output for regerence)
def generate_chapter_pretest(user_id, textbook_id, chapter, llm):
    chapter_id = chapter["id"]
    chapter_title = chapter["title"]

    # check if this chapter already has a pretest
    existing = (
        supabase.table("pretests")
        .select("id")
        .eq("textbook_id", textbook_id)
        .eq("chapter_id", chapter_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        print(f"[pretest] '{chapter_title}' already has a pretest, moving on")
        return

    print(f"[pretest] generating for '{chapter_title}'")

    # Build context from all chunks in this chapter
    context = build_pretest_context(textbook_id, chapter_title)
    if not context.strip():
        print(f"[pretest] no context found for '{chapter_title}', skipping")
        return

    # One LLM call returns all 10 questions at once
    try:
        questions = llm.generate_pretest(context=context, temp=0.3)
    except Exception as e:
        print(f"[pretest] LLM call failed for '{chapter_title}':", repr(e))
        traceback.print_exc()
        return

    if not questions:
        print(f"[pretest] no questions returned for '{chapter_title}'")
        return

    # Write questions to Supabase
    try:
        store_pretest(textbook_id, chapter_id, chapter_title, questions)
        print(f"[pretest] stored {len(questions)} questions for '{chapter_title}'")
    except Exception as e:
        print(f"[pretest] failed to store for '{chapter_title}':", repr(e))
        traceback.print_exc()

def generate_all_pretests(user_id, textbook_id, toc):
    try:
        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        for chapter in toc:
            generate_chapter_pretest(user_id, textbook_id, chapter, llm)
        print("[pretests] all done")
    except Exception as e:
        print("PRETEST GENERATION FAILED:", repr(e))
        traceback.print_exc()

def process_textbook(user_id: str, textbook_id: str, file_bytes: bytes):
    """
    Batch-processing version:
      - Slice PDF into page ranges (prevents Docling blowing up around page ~72)
      - Run Docling+chunking per batch
      - Embed + upsert incrementally
      - Mark ready/partial depending on coverage
    """
    try:
        update_textbook_status(textbook_id, "processing")

        toc = get_toc(textbook_id)
        total_pages = get_textbook_page_count(textbook_id)  # stored during upload via store_toc()

        if not total_pages:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            total_pages = doc.page_count
            doc.close()

        BATCH_PAGES = 15   # start with 10–20; 15 is a good default
        all_chunks = []
        start_index = 0

        # process each batch
        page_start = 1
        while page_start <= total_pages:
            page_end = min(total_pages, page_start + BATCH_PAGES - 1)

            print(f"[process_textbook] batch {page_start}-{page_end} start_index={start_index}")

            batch_pdf = pdf_page_range(file_bytes, page_start, page_end)

            # Docling returns pages relative to the sliced PDF; convert to global pages:
            # local pages are 1..BATCH_PAGES, so offset is (page_start - 1)
            batch_chunks = parse_and_chunk(
                batch_pdf,
                user_id,
                textbook_id,
                toc,
                page_offset=page_start - 1,
                start_index=start_index,
            )

            # Embed+upsert per batch to keep memory stable
            texts = [c["text"] for c in batch_chunks]
            embeddings = []
            for i in range(0, len(texts), 100):
                embeddings.extend(embed_texts(texts[i:i + 100]))

            upsert_chunks(batch_chunks, embeddings)

            all_chunks.extend(batch_chunks)
            start_index += len(batch_chunks)
            page_start = page_end + 1

        # coverage check
        pages = [c.get("page_start") for c in all_chunks if isinstance(c.get("page_start"), int)]
        max_p = max(pages) if pages else None

        status = "ready"
        if max_p is None or (total_pages and max_p < int(0.9 * total_pages)):
            status = "partial"

        print("[process_textbook] done", {"chunks": len(all_chunks), "max_page": max_p, "total_pages": total_pages, "status": status})

        update_textbook_status(textbook_id, status, len(all_chunks))

        # TODO: switch this with the celery implementation so that it can work in the background and generate each pretest
        # This will begin generating pretests for every chapter after the texbok is being parsed entirely (this could later be switched to allow a pretest
        # to be generated the instant the chapter is done being parsed)
        # CELERY: replace with pretest_task.delay(user_id, textbook_id, toc)
        generate_all_pretests(user_id, textbook_id, toc)

    except Exception as e:
        update_textbook_status(textbook_id, "failed")
        print("PROCESS_TEXTBOOK FAILED:", repr(e))
        traceback.print_exc()
        raise
