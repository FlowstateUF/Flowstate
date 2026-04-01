import traceback
import pymupdf
from app.services.embedding_service import embed_texts
from app.services.supabase_service import (
    get_textbook_page_count,
    get_toc,
    update_textbook_status
)
from app.services.textbook_service import (
    parse_and_chunk,
    pdf_page_range
)
from app.services.vector_service import upsert_chunks
from app.services.pretest_processing import generate_all_pretests
from celery import shared_task

@shared_task
def compute_page_coverage(chunks):
    pages = []
    for c in chunks:
        p = c.get("page_start")
        if isinstance(p, int):
            pages.append(p)
            continue

        # fallback 
        p = c.get("page_number")
        if isinstance(p, int):
            pages.append(p)

    return (min(pages), max(pages), len(set(pages))) if pages else (None, None, 0)


@shared_task
def process_textbook(user_id: str, textbook_id: str, file_bytes: bytes):
    """
    Batch-processing version:
      - Slice PDF into page ranges (prevents Docling blowing up around page ~72)
      - Run Docling+chunking per batch
      - Embed + upsert incrementally
      - Mark ready/partial depending on coverage
    """
    try:
        update_textbook_status(textbook_id, "parsing", 0)

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

            update_textbook_status(textbook_id, "parsing", page_end)
            
            page_start = page_end + 1


        # coverage check
        pages = [c.get("page_start") for c in all_chunks if isinstance(c.get("page_start"), int)]
        max_p = max(pages) if pages else None

        final_status = "ready"
        if max_p is None or (total_pages and max_p < int(0.9 * total_pages)):
            final_status = "partial"

        print("[process_textbook] done", {"chunks": len(all_chunks), "max_page": max_p, "total_pages": total_pages, "status": final_status})

        update_textbook_status(textbook_id, "generating_pretests", len(all_chunks))
        print("[process_textbook] generating pretests")

        generate_all_pretests(user_id, textbook_id, toc)

        update_textbook_status(textbook_id, final_status, len(all_chunks))
        print("[process_textbook] complete", {"textbook_id": textbook_id, "status": final_status})

    except Exception as e:
        update_textbook_status(textbook_id, "failed")
        print("PROCESS_TEXTBOOK FAILED:", repr(e))
        traceback.print_exc()
        raise
