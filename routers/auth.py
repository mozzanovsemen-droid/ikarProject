from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
from database import get_connection, hash_password
from auth import create_access_token, verify_token
from models import UserCreate, User
from typing import Annotated

router = APIRouter()
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    if not credentials:
        raise HTTPException(status_code=401, detail="No token")
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id

def get_current_user_role(user_id: int, db: sqlite3.Connection) -> str:
    cursor = db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user['role']

@router.post("/register", response_model=User)
def register(user: UserCreate, db: sqlite3.Connection = Depends(get_connection)):
    try:
        password_hash = hash_password(user.password)
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (user.username, password_hash, user.role)
        )
        user_id = cursor.lastrowid
        db.commit()
        return User(id=user_id, username=user.username, role=user.role)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")

@router.post("/login")
def login(user: UserCreate, db: sqlite3.Connection = Depends(get_connection)):
    cursor = db.execute("SELECT id, password_hash FROM users WHERE username = ?", (user.username,))
    db_user = cursor.fetchone()
    if not db_user or hash_password(user.password) != db_user['password_hash']:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = create_access_token({"user_id": db_user['id']})
    return {"access_token": access_token, "token_type": "bearer"}
