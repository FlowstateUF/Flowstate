from app.clients import qdrant
from app.services.embedding_service import embed_query
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct, PointIdsList
import uuid

def get_collection_info(vector: str):
    return qdrant.get_collection(vector)

def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """Store chunks and their embeddings in Qdrant."""
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector={"dense": embedding},
            payload=chunk
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    qdrant.upsert(collection_name="chunks", points=points)

def retrieve_context(user_id: str, textbook_id: str, query: str, top_k: int = 8, chapter_title: str = None) -> str:
    qvec = embed_query(query)

    must_filters = [
        FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
        FieldCondition(key="textbook_id", match=MatchValue(value=str(textbook_id))),
    ]
    if chapter_title:
        must_filters.append(
            FieldCondition(key="chapter", match=MatchValue(value=chapter_title))
        )

    flt = Filter(must=must_filters)
    

    res = qdrant.query_points(
        collection_name="chunks",
        query=qvec,
        using="dense",
        query_filter=flt,
        limit=top_k,
        with_payload=True,
    )

    hits = res.points or []
    if not hits:
        return ""

    parts = []
    for p in hits:
        payload = p.payload or {}
        text = (payload.get("text") or payload.get("content") or "").strip()
        if not text:
            continue

        citation = payload.get("citation")
        if not citation:
            ps = payload.get("page_start") or payload.get("page_number")
            pe = payload.get("page_end")
            if ps is not None:
                citation = f"Page {ps}" if pe in (None, ps) else f"Pages {ps}-{pe}"

        parts.append(f"{citation}: {text}" if citation else text)

    return "\n\n".join(parts)

def fetch_all_chunks(textbook_id: str, chapter_title: str, user_id: str) -> list[dict]:
    # Filter to only this chapter's chunks
    flt = Filter(must=[
        FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
        FieldCondition(key="textbook_id", match=MatchValue(value=str(textbook_id))),
        FieldCondition(key="chapter", match=MatchValue(value=chapter_title))
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

    return all_results

def delete_textbook_chunks(user_id: str, textbook_id: str):
    flt = Filter(must=[
        FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
        FieldCondition(key="textbook_id", match=MatchValue(value=str(textbook_id))),
    ])

    all_ids = []
    offset = None

    while True:
        results, offset = qdrant.scroll(
            collection_name="chunks",
            scroll_filter=flt,
            limit=100,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )

        all_ids.extend([point.id for point in results if point.id is not None])

        if offset is None:
            break

    if all_ids:
        qdrant.delete(
            collection_name="chunks",
            points_selector=PointIdsList(points=all_ids),
        )