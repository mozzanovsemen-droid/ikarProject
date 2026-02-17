from typing import List
from typing_extensions import Annotated
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
from database import get_connection, init_db, hash_password
from auth import verify_token, create_access_token
import models

app = FastAPI()
security = HTTPBearer(auto_error=False)


def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="No token provided")

    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


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
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, password_hash)
        )
        user_id = cursor.lastrowid
        db.commit()
        return models.User(id=user_id, username=user.username)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")


@app.post("/login")
def login(user: models.UserCreate, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "SELECT id, password_hash FROM users WHERE username = ?",
        (user.username,)
    )
    db_user = cursor.fetchone()

    if not db_user or hash_password(user.password) != db_user['password_hash']:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token({"user_id": db_user['id']})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/notes", response_model=List[models.Note])
def get_my_notes(user_id: int = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute(
        "SELECT * FROM notes WHERE owner_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    notes = [dict(row) for row in cursor.fetchall()]
    return notes


@app.post("/notes", response_model=models.Note, status_code=status.HTTP_201_CREATED)
def create_my_note(
        note: models.NoteCreate,
        user_id: int = Depends(get_current_user),
        db: sqlite3.Connection = Depends(get_db)
):
    cursor = db.execute(
        "INSERT INTO notes (title, content, owner_id) VALUES (?, ?, ?)",
        (note.title, note.content, user_id)
    )
    note_id = cursor.lastrowid
    db.commit()
    cursor = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    return dict(cursor.fetchone())


@app.get("/notes/{note_id}", response_model=models.Note)
def get_my_note(note_id: int, user_id: int = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("SELECT * FROM notes WHERE id = ? AND owner_id = ?", (note_id, user_id))
    note = cursor.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(note)


@app.delete("/notes/{note_id}")
def delete_my_note(note_id: int, user_id: int = Depends(get_current_user), db: sqlite3.Connection = Depends(get_db)):
    cursor = db.execute("DELETE FROM notes WHERE id = ? AND owner_id = ?", (note_id, user_id))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted"}


@app.get("/admin/notes", response_model=List[models.Note])
def get_all_notes(
        admin_key: str = "not_admin",
        x_debug: bool = Header(default=False, alias="X-Debug"),
        db: sqlite3.Connection = Depends(get_db)
):

    if admin_key != "superadmin":
        raise HTTPException(status_code=403, detail=f"Admin key required. Got: '{admin_key}'")

    cursor = db.execute("SELECT * FROM notes ORDER BY created_at DESC")
    notes = [dict(row) for row in cursor.fetchall()]

    if x_debug:
        return {"debug": f"Total notes: {len(notes)}", "notes": notes}
    return notes

