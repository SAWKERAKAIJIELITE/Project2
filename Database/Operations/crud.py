from sqlalchemy.orm import Session
from .. import models, schemas
from passlib.context import CryptContext
from datetime import datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password: str | bytes = pwd_context.hash(user.password)
    db_user = models.User(
        email=user.email, hashed_password=hashed_password, username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_documents(db: Session, user_id: int):
    return db.query(models.Document).filter(models.Document.owner_id == user_id).all()


# def get_document_by_name(db: Session, user_id: int, document_name: str):
#     return db.query(models.Document).filter(
#         models.Document.owner_id == user_id
#     ).filter(
#         models.Document.name == document_name
#     ).first()


def get_document(db: Session, user_id: int, document_id: int):
    return db.query(models.Document).filter(
        models.Document.owner_id == user_id
    ).filter(
        models.Document.id == document_id
    ).first()


def create_user_document(db: Session, document: schemas.DocumentCreate, user_id: int):
    db_document = models.Document(**document.model_dump(), owner_id=user_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def delete_document(db: Session, user_id: int, document_id: int):
    delete_document_notes(db, document_id)
    i = db.query(models.Document).filter(
        models.Document.owner_id == user_id
    ).filter(
        models.Document.id == document_id
    ).delete()
    db.commit()
    if i == 1:
        return True
    return False


def update_document(db: Session, document_path: str):
    now = datetime.now(timezone.utc)
    i = db.query(models.Document).filter(
        models.Document.video_path == document_path
    ).update({"updated_at": now})
    db.commit()
    # return get_document(db, user_id, document_id)
    if i == 1:
        return True
    return False


def create_document_note(db: Session, note: schemas.NoteCreate, document_id: int):
    db_note = models.Note(**note.model_dump(), document_id=document_id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def get_user_notes(db: Session, user_id: int):

    documents = db.query(models.Document).filter(
        models.Document.owner_id == user_id
    ).all()

    all_notes = []
    for document in documents:
        notes = db.query(models.Note).filter(
            models.Note.document_id == document.id
        ).all()
        for note in notes:
            notee = {
                "id": note.id,
                "note_name": note.name,
                "note_content": note.content,
                "document_name": document.name,
                "created_at": str(note.created_at),
                "updated_at": str(note.updated_at)
            }
            all_notes.append(notee)

    return all_notes


def delete_document_notes(db: Session, document_id: int):
    db.query(models.Note).filter(
        models.Note.document_id == document_id
    ).delete()
    db.commit()


def delete_document_note(db: Session, note_id: int):
    db.query(models.Note).filter(
        models.Note.id == note_id
    ).delete()
    db.commit()
