from app.services import get_toc, parse_and_chunk, embed_texts, upsert_chunks, update_textbook_status

def process_textbook(textbook_id: str, file_bytes: bytes):
    """
    Runs in a background thread immediately after upload.

    Flow:
      1. Fetch TOC already stored in Supabase during upload
      2. Run Docling on the full textbook
      3. Embed all chunks in batches of 100
      4. Store chunks & vectors in Qdrant
      5. Update document status to ready
    """
    try:
        toc = get_toc(textbook_id)

        chunks = parse_and_chunk(file_bytes, textbook_id, toc)

        texts = [c["text"] for c in chunks]
        embeddings = []
        for i in range(0, len(texts), 100):
            embeddings.extend(embed_texts(texts[i:i + 100]))

        upsert_chunks(chunks, embeddings)
        update_textbook_status(textbook_id, "ready", len(chunks))

    except Exception as e:
        update_textbook_status(textbook_id, "failed")
        raise e