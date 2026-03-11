from flask import Flask
from flask_cors import CORS
from app.config import settings
from app.clients import init_supabase, init_qdrant
from app.celery_app import celery_init_app
from flask_jwt_extended import JWTManager
import os

# Initalize Flask app, database, and CORS settings

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
    app.config["CELERY"] = {
        "broker_url": os.environ.get("REDIS_URL", "redis://localhost:6379"), 
        "result_backend": os.environ.get("REDIS_URL", "redis://localhost:6379")
    }

    init_supabase()
    init_qdrant()

    celery_init_app(app)
    
    jwt = JWTManager(app)

    CORS(app, resources={r"/*": {"origins": ["http://localhost:5173","http://localhost:3000"]}})
    
    # Register routes
    from app import routes
    routes.register_routes(app)
    
    return app