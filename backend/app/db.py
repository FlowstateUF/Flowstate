from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    
    # Creates DB and all tables (only if they already do not exist)
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database initialized successfully!")