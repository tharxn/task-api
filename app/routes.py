from fastapi import APIRouter, HTTPException, Response
from app.models import TaskCreate, TaskUpdate

router = APIRouter()


@router.get("/", summary="API Information")
def root():
    return {
        "name": "CRUD API",
        "version": "1.0",
        "endpoints": [
            "/health",
            "/tasks"
        ]
    }

@router.get("/health", summary="Health Check")
def health():
    return {
        "status": "ok"
    }


@router.get("/tasks", summary="Get all tasks")
def get_tasks():
    return tasks


@router.get("/tasks/{task_id}", summary="Get a task by ID")
def get_task(task_id: int):

    for task in tasks:
        if task["id"] == task_id:
            return task

    raise HTTPException(
        status_code=404,
        detail=f"Task {task_id} not found"
    )


@router.post("/tasks", status_code=201, summary="Create a task")
def create_task(task: TaskCreate):

    if task.title.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty"
        )

    new_task = {
        "id": max([t["id"] for t in tasks], default=0) + 1,
        "title": task.title,
        "done": False
    }

    tasks.append(new_task)

    return new_task


@router.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, updated: TaskUpdate):

    for task in tasks:

        if task["id"] == task_id:

            if updated.title is not None:

                if updated.title.strip() == "":
                    raise HTTPException(
                        status_code=400,
                        detail="Title cannot be empty"
                    )

                task["title"] = updated.title

            if updated.done is not None:
                task["done"] = updated.done

            return task

    raise HTTPException(
        status_code=404,
        detail=f"Task {task_id} not found"
    )


@router.delete(
    "/tasks/{task_id}",
    status_code=204,
    summary="Delete a task"
)
def delete_task(task_id: int):

    for i, task in enumerate(tasks):

        if task["id"] == task_id:
            tasks.pop(i)
            return Response(status_code=204)

    raise HTTPException(
        status_code=404,
        detail=f"Task {task_id} not found"
    )