from flask import Flask
from flask_cors import CORS
from app.db import init_db

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flowstate.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
    init_db(app)
    
    # Register routes
    from app import routes
    routes.register_routes(app)
    
    return app