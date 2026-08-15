from fastapi import APIRouter, HTTPException
from app.database import get_connection

from app.models import TaskCreate
from app.models import TaskUpdate
from fastapi import Response

router = APIRouter()


@router.get("/")
def root():
    return {
        "name": "Task API",
        "version": "2.0",
        "endpoints": ["/tasks"]
    }


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/tasks")
def get_tasks():

    conn = get_connection()
    cursor = conn.cursor()

    cur.execute("SELECT id, title, done FROM tasks ORDER BY id")

    rows = cursor.fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"])
        }
        for row in rows
    ]


@router.get("/tasks/{task_id}")
def get_task(task_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cur.execute(
        "SELECT id, title, done FROM tasks WHERE id=%s",
        (task_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"])
    }


@router.post("/tasks", status_code=201)
def create_task(task: TaskCreate):

    if task.title.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cur.execute(
        """
        INSERT INTO tasks(title, done)
        VALUES (%s, %s)
        RETURNING id
        """,
        (task.title, False)
    )

    task_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    return {
        "id": task_id,
        "title": task.title,
        "done": False
    }

@router.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):

    conn = get_connection()
    cursor = conn.cursor()

    cur.execute(
        """
        UPDATE tasks
        SET title=%s, done=%s
        WHERE id=%s
        """,
        (title, done, task_id)
    )

    existing = cursor.fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    title = task.title if task.title is not None else existing["title"]

    if title.strip() == "":
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty"
        )

    done = task.done if task.done is not None else bool(existing["done"])

    cursor.execute(
        """
        UPDATE tasks
        SET title=?, done=?
        WHERE id=?
        """,
        (title, int(done), task_id)
    )

    conn.commit()
    conn.close()

    return {
        "id": task_id,
        "title": title,
        "done": done
    }

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cur.execute(
        "DELETE FROM tasks WHERE id=%s",
        (task_id,)
    )   

    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    cursor.execute(
        "DELETE FROM tasks WHERE id=?",
        (task_id,)
    )

    conn.commit()
    conn.close()

    return Response(status_code=204)