import traceback
from app.services import get_toc, parse_and_chunk, embed_texts, upsert_chunks, update_textbook_status, get_textbook_page_count, pdf_page_range

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
            # fallback: if page_count wasn't stored, just assume 1 batch
            total_pages = 999999

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

    except Exception as e:
        update_textbook_status(textbook_id, "failed")
        print("PROCESS_TEXTBOOK FAILED:", repr(e))
        traceback.print_exc()
        raise