from typing import Annotated

from fastapi import APIRouter, Depends
from models import STaskAdd
from repository import TaskRepository

router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.post("")
async def add_task(
        task: Annotated[STaskAdd, Depends()],
):
    task_id = await TaskRepository.add_one(task)
    return {"ok": True, "task_id": task_id}

@router.get("")
async def get_task():
    tasks = await TaskRepository.find_all()
    return {"tasks": tasks}



