from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class NoteBase(BaseModel):
    name: str
    content: str


class NoteCreate(NoteBase):
    created_at: datetime
    updated_at: datetime


class Note(NoteBase):
    id: int
    document_id: int

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    name: str
    typ: str = Field(pattern="transcription|structuring")


class DocumentCreate(DocumentBase):
    video_path: str
    created_at: datetime
    updated_at: datetime


class Document(DocumentBase):
    id: int
    owner_id: int
    notes: list[Note] = []

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    # is_active: bool
    documents: list[Document] = []

    class Config:
        from_attributes = True
