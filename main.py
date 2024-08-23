from datetime import datetime, timedelta, timezone
from os import mkdir, listdir, remove
from typing import Annotated, Mapping
from sqlalchemy.orm import Session
from fastapi import Body, FastAPI, status, Depends, HTTPException, UploadFile, Query, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from starlette.background import BackgroundTask
import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from Database.Operations import crud
from Database import models, schemas
from Database.database import SessionLocal, engine


class LoginUser(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str


class ResponseModel(JSONResponse):
    def __init__(
        self,
        message: str,
        token: Token | dict | None = None,
        data: BaseModel | dict | list | None = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ):
        super().__init__(
            {"Message": message, "token": token, "data": data},
            status_code, headers, media_type, background
        )


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="new/user")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "64be62a921e3050384ff8f6286af4ffeef3a91369099bc03b142f97b451e1715"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 15

models.Base.metadata.create_all(bind=engine)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: timedelta | None = None):

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=15)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def generate_token(data: str):

    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": data}, expires_delta=access_token_expires)
    token = Token(access_token=access_token, token_type="bearer")
    return token


def verify_password(plain_password: str | bytes, hashed_password: str | bytes):
    return pwd_context.verify(plain_password, hashed_password)


def handle_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError as exe:
        raise credentials_exception from exe
    db_user = crud.get_user_by_username(db, token_data.username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


app = FastAPI()


@app.post('/new/user')
def sign_up(
        username: Annotated[str, Form()],
        email: Annotated[str, Form()],
        password: Annotated[str, Form()],
        # user: schemas.UserCreate,
        db: Annotated[Session, Depends(get_db)]
) -> ResponseModel:

    db_user = crud.get_user_by_email(db, email=email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = crud.create_user(
        db,
        schemas.UserCreate(username=username, email=email, password=password)
    )

    token = generate_token(username)

    d = {"id": db_user.id, "username": db_user.username, "email": db_user.email}

    return ResponseModel("Created Successfully", token.model_dump(), d, status_code=status.HTTP_201_CREATED)


@app.post("/login")
def log_in(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    # user: LoginUser,
    db: Annotated[Session, Depends(get_db)]
) -> ResponseModel:

    db_user = crud.get_user_by_username(db, username)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = generate_token(username)

    d = {"id": db_user.id, "username": db_user.username, "email": db_user.email}

    return ResponseModel("login finished Successfully", token.model_dump(), d, status_code=status.HTTP_200_OK)


@app.post("/users/me/documents/new")
async def create_document_for_user(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    document_name: Annotated[str, Query()],
    document_typ: Annotated[str, Query()],
    video: UploadFile,
    db: Session = Depends(get_db)
):
    content = await video.read()
    # TODO Send Content to the Model
    list_dir = listdir('./Storage/')
    if db_user.username not in list_dir:
        mkdir(f'./Storage/{db_user.username}')

    video_path = f'./Storage/{db_user.username}/'+video.filename
    try:
        f = open(video_path, 'x')
    except FileExistsError as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f'{video.filename} Already Exist'
        ) from exc

    # TODO Recieve the Generated Content to the File
    f.write(content.hex())
    f.close()

    now = datetime.now(timezone.utc)
    doc = schemas.DocumentCreate(
        name=document_name, typ=document_typ, video_path=video_path, created_at=now, updated_at=now
    )

    crud.create_user_document(db=db, document=doc, user_id=db_user.id)

    dur = 0
    return ResponseModel(
        f"Created Successfully\nRemaining time to generate document:{dur}",
        status_code=status.HTTP_201_CREATED
    )


@app.get("/users/me/documents")
def read_documents(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    db: Session = Depends(get_db)
):
    items = crud.get_documents(db, db_user.id)
    documents = []
    for item in items:
        f = open(f'{item.video_path}', 'r')
        content = f.read()
        document = {
            "id": item.id,
            "name": item.name,
            "created_at": str(item.created_at),
            "updated_at": str(item.updated_at),
            "Content": content
        }
        f.close()
        documents.append(document)
    return ResponseModel("get My Drive Successfully", data=documents, status_code=200)


@app.put('/users/me/documents/update')
async def update_document_content(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    video: UploadFile,
    db: Session = Depends(get_db)
):
    content = await video.read()
    video_path = f'./Storage/{db_user.username}/'+video.filename

    f = open(video_path, 'w')
    f.write(content.hex())
    f.close()

    updated_document = crud.update_document(db, video_path)
    if updated_document:
        return ResponseModel("Updated Successfully", status_code=status.HTTP_200_OK)
    return ResponseModel("Updated Failed", status_code=status.HTTP_424_FAILED_DEPENDENCY)


@app.delete('/users/me/documents/delete/{document_id}')
def delete_document(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    document_id: int,
    db: Session = Depends(get_db)
):
    video_path = crud.get_document(db, db_user.id, document_id).video_path
    is_delelted = crud.delete_document(db, db_user.id, document_id)
    if is_delelted:
        remove(video_path)
        return ResponseModel("Deleted Successfully", status_code=status.HTTP_200_OK)
    return ResponseModel("Deleted Failed", status_code=status.HTTP_424_FAILED_DEPENDENCY)


@app.post('/users/me/documents/{document_id}/notes/new')
def create_note_for_document(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    document_id: int,
    name: Annotated[str, Form()],
    content: Annotated[str, Form()],
    # note: schemas.NoteBase,
    db: Session = Depends(get_db)
):
    # TODO Ensure that param(document_id) exist in User Documents' ids
    now = datetime.now(timezone.utc)
    note_in = schemas.NoteCreate(
        name=name, content=content, created_at=now, updated_at=now
    )
    db_note = crud.create_document_note(db, note_in, document_id)
    if db_note:
        return ResponseModel("Created Successfully", status_code=status.HTTP_201_CREATED)
    return ResponseModel("Created Failed", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get('/users/me/documents/notes')
def read_notes_of_user(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    db: Session = Depends(get_db)
):
    notes = crud.get_user_notes(db, db_user.id)
    return ResponseModel("get My Notes Successfully", data=notes, status_code=200)


@app.delete('/users/me/documents/notes/{note_id}/delete')
def name(
    db_user: Annotated[schemas.User, Depends(handle_token)],
    note_id: int,
    db: Session = Depends(get_db)
):
    # TODO Ensure that param(note_id) exist in User Documents' ids
    crud.delete_document_note(db, note_id)
    return ResponseModel("Deleted Successfully", status_code=status.HTTP_200_OK)
