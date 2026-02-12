import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    NAVIGATOR_API_KEY = os.getenv("NAVIGATOR_API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

settings = Settings()

if not settings.NAVIGATOR_API_KEY:
    raise RuntimeError("missing NAVIGATOR_API_KEY. create a backend/.env and set it.")
