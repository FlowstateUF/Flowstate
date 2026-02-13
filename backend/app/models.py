from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .db import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    documents = db.relationship('Document', backref='user', lazy=True)
    generated_content = db.relationship('GeneratedContent', backref='user', lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(255), nullable=False)

    parsed = db.Column(db.Boolean, default=False)
    file_size = db.Column(db.Integer)
    page_count = db.Column(db.Integer)
    mime_type = db.Column(db.String(50)) # Not sure if needed
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    chunks = db.relationship('Chunk', backref='document', lazy=True)
    generated_content = db.relationship('GeneratedContent', backref='document', lazy=True)

class Chunk(db.Model):
    __tablename__ = 'chunks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    token_count = db.Column(db.Integer)

class GeneratedContent(db.Model):
    __tablename__ = 'generated_content'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    content_type = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)