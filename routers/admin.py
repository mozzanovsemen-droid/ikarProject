from fastapi import APIRouter, Depends, HTTPException
from typing import List
import sqlite3
from database import get_connection
from models import User, ReportResponse

router = APIRouter()

@router.get("/users", response_model=List[User])
def get_all_users(admin_key: str = "not_admin", db=Depends(get_connection)):
    if admin_key != "superadmin":
        raise HTTPException(status_code=403, detail="Admin access required")
    cursor = db.execute("SELECT id, username, role FROM users ORDER BY id")
    return [dict(row) for row in cursor.fetchall()]

@router.get("/student/{student_id}/reports", response_model=List[ReportResponse])
def get_student_reports(student_id: int, admin_key: str = "not_admin", db=Depends(get_connection)):
    if admin_key != "superadmin":
        raise HTTPException(status_code=403, detail="Admin access required")
    cursor = db.execute(
        "SELECT *, datetime(created_at, 'unixepoch') as created_at, datetime(updated_at, 'unixepoch') as updated_at FROM reports WHERE student_id = ? ORDER BY updated_at DESC",
        (student_id,)
    )
    return [dict(row) for row in cursor.fetchall()]

@router.get("/reports", response_model=List[ReportResponse])
def get_all_reports(admin_key: str = "not_admin", db=Depends(get_connection)):
    if admin_key != "superadmin":
        raise HTTPException(status_code=403, detail="Admin access required")
    cursor = db.execute(
        "SELECT *, datetime(created_at, 'unixepoch') as created_at, datetime(updated_at, 'unixepoch') as updated_at FROM reports ORDER BY updated_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]
