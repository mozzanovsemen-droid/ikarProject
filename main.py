from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Header, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import sqlite3
import os
import shutil
import uuid

from database import get_connection, init_db, hash_password
from auth import verify_token, create_access_token
import models
from router import router as tasks_router

app = FastAPI()
security = HTTPBearer(auto_error=False)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def read_index():
    return FileResponse("frontend/templates/index.html")


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="No token provided")
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


def get_current_user_data(user_id: int = Depends(get_current_user_id),
                          db: sqlite3.Connection = Depends(get_connection)):
    cursor = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/register", response_model=models.User)
def register(user: models.UserCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        password_hash = hash_password(user.password)
        role = "teacher" if user.is_teacher else "student"
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (user.username, password_hash, role)
        )
        user_id = cursor.lastrowid
        db.commit()
        return models.User(id=user_id, username=user.username, role=role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято!")


@app.post("/login")
def login(user: models.UserCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "SELECT id, password_hash, role FROM users WHERE username = ?",
        (user.username,)
    )
    db_user = cursor.fetchone()
    if not db_user or hash_password(user.password) != db_user['password_hash']:
        raise HTTPException(status_code=400, detail="Неверные данные")
    access_token = create_access_token({"user_id": db_user['id']})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user['role']
    }


# студенты

@app.get("/notes", response_model=List[models.Note])
def get_my_notes(user_id: int = Depends(get_current_user_id), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "SELECT * FROM notes WHERE owner_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return [dict(row) for row in cursor.fetchall()]


@app.post("/notes", response_model=models.Note, status_code=status.HTTP_201_CREATED)
def create_my_note(
        title: str = Form(...),
        content: str = Form(...),
        attachment: UploadFile = File(None),
        user_data: dict = Depends(get_current_user_data),
        db: sqlite3.Connection = Depends(get_db)
):
    if user_data['role'] == 'teacher':
        raise HTTPException(status_code=403, detail="Преподаватели не создают задачи, а проверяют их.")

    attachment_url = None
    if attachment and attachment.filename:
        file_extension = os.path.splitext(attachment.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = f"uploads/{unique_filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)
        attachment_url = f"/uploads/{unique_filename}"

    cursor = db.execute(
        "INSERT INTO notes (title, content, owner_id, status, attachment_url) VALUES (?, ?, ?, 'pending', ?)",
        (title, content, user_data['id'], attachment_url)
    )
    note_id = cursor.lastrowid
    db.commit()
    cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    return dict(cursor.fetchone())


@app.get("/notes/{note_id}", response_model=models.Note)
def get_my_note(note_id: int, user_id: int = Depends(get_current_user_id), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note['owner_id'] != user_id:
        pass
    return dict(note)


@app.delete("/notes/{note_id}")
def delete_my_note(note_id: int, user_id: int = Depends(get_current_user_id), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("DELETE FROM notes WHERE id = ? AND owner_id = ?", (note_id, user_id))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted"}


# для преподавателей

@app.get("/teacher/students", response_model=List[models.User])
def get_all_students(
        user_data: dict = Depends(get_current_user_data),
        db: sqlite3.Connection = Depends(get_db)
):
    if user_data['role'] != 'teacher':
        raise HTTPException(status_code=403, detail="Доступ только для преподавателей")

    cursor = db.execute("SELECT id, username, role FROM users WHERE role = 'student'")
    return [dict(row) for row in cursor.fetchall()]


@app.get("/teacher/students/{student_id}/notes", response_model=List[models.Note])
def get_student_notes(
        student_id: int,
        user_data: dict = Depends(get_current_user_data),
        db: sqlite3.Connection = Depends(get_db)
):
    if user_data['role'] != 'teacher':
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    cursor = db.execute("SELECT * FROM notes WHERE owner_id = ? ORDER BY created_at DESC", (student_id,))
    return [dict(row) for row in cursor.fetchall()]


@app.patch("/teacher/notes/{note_id}/status")
def update_note_status(
        note_id: int,
        status_update: models.NoteUpdateStatus,
        user_data: dict = Depends(get_current_user_data),
        db: sqlite3.Connection = Depends(get_db)
):
    if user_data['role'] != 'teacher':
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    cursor = db.execute("UPDATE notes SET status = ? WHERE id = ?", (status_update.status, note_id))
    db.commit()
    return {"ok": True, "status": status_update.status}


app.include_router(tasks_router)

