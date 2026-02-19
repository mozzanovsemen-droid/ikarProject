from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class RoleEnum(str, Enum):
    student = "student"
    teacher = "teacher"

class UserCreate(BaseModel):
    username: str
    password: str
    role: RoleEnum

class User(BaseModel):
    id: int
    username: str
    role: RoleEnum

class ReportStatusEnum(str, Enum):
    draft = "draft"
    in_review = "in_review"
    reviewed = "reviewed"
    needs_revision = "needs_revision"

class ReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[ReportStatusEnum] = None

class ReportResponse(BaseModel):
    id: int
    title: str
    content: str
    status: ReportStatusEnum
    student_id: int
    teacher_id: Optional[int]
    created_at: datetime
    updated_at: datetime
=======
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)


class NoteCreate(NoteBase):
    pass


class Note(NoteBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
