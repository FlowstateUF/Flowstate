import uuid
from qdrant_client.models import PointStruct
from app.clients import qdrant


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