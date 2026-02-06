from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    
    # Creates DB and all tables (only if they already do not exist)
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")

# ** Database Models / Tables **

# Example user table, can be modified
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)