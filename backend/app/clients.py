from supabase import create_client, Client
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sympy import public
from app.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

qdrant = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)


# Supabase PostgreSQL database is initialized within Supabase dashboard, schema is provided in database/schema.sql
def init_supabase():
    buckets = supabase.storage.list_buckets()
    bucket_names = {bucket.name for bucket in buckets}

    if "textbooks" not in bucket_names:
        supabase.storage.create_bucket(
            "textbooks", 
            options={
                "public": False,
                "allowed_mime_types": ["application/pdf"]
            }
        )
        print("Created textbooks bucket in Supabase storage")


def init_qdrant():
    existing = {c.name for c in qdrant.get_collections().collections}

    if "chunks" not in existing:
        qdrant.create_collection(
            collection_name="chunks",
            vectors_config={
                "dense": VectorParams(
                    size=384, 
                    distance=Distance.COSINE, 
                    on_disk=True
                )
            }
        )

        qdrant.create_payload_index(collection_name="chunks", field_name="user_id", field_schema="keyword", field_name_in_tenant=True)
        qdrant.create_payload_index(collection_name="chunks", field_name="textbook_id", field_schema="keyword")
        qdrant.create_payload_index(collection_name="chunks", field_name="page", field_schema="integer")

