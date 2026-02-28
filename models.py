from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    is_teacher: Optional[bool] = False

class User(BaseModel):
    id: int
    username: str
    role: str

class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)
    attachment_url: Optional[str] = None

class NoteCreate(NoteBase):
    pass

class NoteUpdateStatus(BaseModel):
    status: str

class Note(NoteBase):
    id: int
    owner_id: int
    created_at: datetime
    status: str = "pending"

    class Config:
        from_attributes = True

class STaskAdd(BaseModel):
    name: str
    description: Optional[str] = None

class STask(STaskAdd):
    id: int
