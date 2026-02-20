import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    NAVIGATOR_API_KEY = os.getenv("NAVIGATOR_API_KEY")

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

settings = Settings()

if not settings.NAVIGATOR_API_KEY:
    raise RuntimeError("missing NAVIGATOR_API_KEY. create a backend/.env and set it.")
if not settings.SUPABASE_URL:
    raise RuntimeError("missing SUPABASE_URL. create a backend/.env and set it.")
if not settings.SUPABASE_SERVICE_KEY:
    raise RuntimeError("missing SUPABASE_SERVICE_KEY. create a backend/.env and set it.")