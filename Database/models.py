from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    # is_active = Column(Boolean, default=True)

    documents = relationship("Document", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    typ = Column(String)
    video_path = Column(String, unique=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    owner = relationship("User", back_populates="documents")
    notes = relationship("Note", back_populates="document")


class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    content = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    document_id = Column(Integer, ForeignKey("documents.id"))

    document = relationship("Document", back_populates="notes")
