from app.db import db
from app.models import Document

def create_document_record(user_id: int, filename: str, storage_path: str) -> Document:
    try:
        doc = Document(
            user_id=user_id,
            filename=filename,
            storage_path=storage_path
        )

        db.session.add(doc)
        db.session.commit()

        return doc
    
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to create document record: {e}")