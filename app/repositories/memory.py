from threading import Lock

from app.repository import Task


class InMemoryTaskRepository:
    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._lock = Lock()

    def list(self) -> list[Task]:
        with self._lock:
            return [task.copy() for task in self._tasks.values()]

    def get(self, task_id: int) -> Task | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.copy() if task is not None else None

    def create(self, title: str) -> Task:
        with self._lock:
            task = Task(id=self._next_id, title=title, done=False)
            self._tasks[task["id"]] = task
            self._next_id += 1
            return task.copy()

    def update(
        self, task_id: int, title: str | None, done: bool | None
    ) -> Task | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if title is not None:
                task["title"] = title
            if done is not None:
                task["done"] = done
            return task.copy()

    def delete(self, task_id: int) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None
