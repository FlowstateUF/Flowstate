import uuid
from qdrant_client.models import PointStruct
from app.clients import qdrant


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]):
    """Store chunks and their embeddings in Qdrant."""
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "text": chunk["text"],
                "doc_id": chunk["doc_id"],
                "chapter": chunk["chapter"],
                "page": chunk["page"],
                "section": chunk["section"],
                "chunk_index": chunk["chunk_index"]
            }
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    qdrant.upsert(collection_name="chunks", points=points)