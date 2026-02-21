from supabase import create_client, Client
from qdrant_client import QdrantClient
from app.config import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

qdrant = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)