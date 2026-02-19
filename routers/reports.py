from fastapi import APIRouter, Depends, HTTPException
from typing import List
import sqlite3
from database import get_connection
from models import ReportCreate, ReportUpdate, ReportResponse, User
from routers.auth import get_current_user, get_current_user_role

router = APIRouter()


def get_report(report_id: int, db: sqlite3.Connection) -> dict:
    cursor = db.execute(
        "SELECT *, datetime(created_at, 'unixepoch') as created_at, datetime(updated_at, 'unixepoch') as updated_at FROM reports WHERE id = ?",
        (report_id,)
    )
    report = cursor.fetchone()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return dict(report)


@router.post("/reports", response_model=ReportResponse, status_code=201)
def create_report(report: ReportCreate, user_id=Depends(get_current_user), db=Depends(get_connection)):
    role = get_current_user_role(user_id, db)
    if role != "student":
        raise HTTPException(status_code=403, detail="Only students can create reports")

    cursor = db.execute(
        "INSERT INTO reports (title, content, status, student_id) VALUES (?, ?, 'draft', ?)",
        (report.title, report.content, user_id)
    )
    report_id = cursor.lastrowid
    db.commit()
    return get_report(report_id, db)


# 🔥 СТУДЕНТ/УЧИТЕЛЬ: Мои отчёты ✅ ИСПРАВЛЕНО!
@router.get("/my-reports")
def get_my_reports(user_id=Depends(get_current_user), db=Depends(get_connection)):
    cursor = db.execute(
        "SELECT *, datetime(created_at, 'unixepoch') as created_at, datetime(updated_at, 'unixepoch') as updated_at FROM reports WHERE student_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    reports = [dict(row) for row in cursor.fetchall()]
    print(f"DEBUG: Found {len(reports)} reports for user {user_id}")
    return reports  # ← УБРАЛ response_model!


# 🔥 СТУДЕНТ: Редактировать свой отчёт
@router.put("/reports/{report_id}", response_model=ReportResponse)
def student_update_report(report_id: int, update_data: ReportUpdate, user_id=Depends(get_current_user),
                          db=Depends(get_connection)):
    role = get_current_user_role(user_id, db)
    if role != "student":
        raise HTTPException(status_code=403, detail="Only students can edit their reports")

    report = get_report(report_id, db)
    if report['student_id'] != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own reports")

    set_fields = []
    params = []

    if update_data.title:
        set_fields.append("title = ?")
        params.append(update_data.title)
    if update_data.content:
        set_fields.append("content = ?")
        params.append(update_data.content)

    if not set_fields:
        raise HTTPException(status_code=400, detail="Title or content required")

    params.extend(["draft", report_id])
    query = f"UPDATE reports SET {', '.join(set_fields)}, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"

    cursor = db.execute(query, params)
    db.commit()
    return get_report(report_id, db)



@router.put("/reports/{report_id}/status", response_model=ReportResponse)
def teacher_update_status(report_id: int, status_data: ReportUpdate, user_id=Depends(get_current_user),
                          db=Depends(get_connection)):
    role = get_current_user_role(user_id, db)
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can update status")

    if not status_data.status:
        raise HTTPException(status_code=400, detail="Status required")

    get_report(report_id, db)

    cursor = db.execute(
        "UPDATE reports SET status = ?, teacher_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status_data.status, user_id, report_id)
    )
    db.commit()
    return get_report(report_id, db)

@router.get("/students")
def get_all_students(user_id=Depends(get_current_user), db=Depends(get_connection)):
    role = get_current_user_role(user_id, db)
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can see all students")

    cursor = db.execute("SELECT id, username, role FROM users WHERE role = 'student' ORDER BY username")
    students = [dict(row) for row in cursor.fetchall()]
    print(f"DEBUG: Found {len(students)} students for teacher {user_id}")
    return students
