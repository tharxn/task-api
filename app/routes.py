from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_task_service
from app.models import TaskCreate, TaskUpdate
from app.service import TaskService

router = APIRouter()
Service = Annotated[TaskService, Depends(get_task_service)]


@router.get("/")
def root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/tasks")
def get_tasks(service: Service):
    return service.list()


@router.get("/tasks/{task_id}")
def get_task(task_id: int, service: Service):
    return service.get(task_id)


@router.post("/tasks", status_code=201)
def create_task(task: TaskCreate, service: Service):
    return service.create(task.title)


@router.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate, service: Service):
    return service.update(task_id, task.title, task.done)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, service: Service):
    service.delete(task_id)
    return Response(status_code=204)
