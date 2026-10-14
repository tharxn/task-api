from app.repository import Task, TaskRepository


class TaskNotFound(LookupError):
    pass


class InvalidTitle(ValueError):
    pass


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def list(self) -> list[Task]:
        return self.repository.list()

    def get(self, task_id: int) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFound("Task not found")
        return task

    def create(self, title: str) -> Task:
        self._validate_title(title)
        return self.repository.create(title)

    def update(
        self, task_id: int, title: str | None, done: bool | None
    ) -> Task:
        self.get(task_id)
        if title is not None:
            self._validate_title(title)
        task = self.repository.update(task_id, title, done)
        if task is None:
            raise TaskNotFound("Task not found")
        return task

    def delete(self, task_id: int) -> None:
        if not self.repository.delete(task_id):
            raise TaskNotFound("Task not found")

    @staticmethod
    def _validate_title(title: str) -> None:
        if not title.strip():
            raise InvalidTitle("Title cannot be empty")
