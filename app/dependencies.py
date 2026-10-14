from app.repositories.postgres import PostgresTaskRepository
from app.service import TaskService

# Storage is selected only here. Both repositories implement TaskRepository.
task_service = TaskService(PostgresTaskRepository())


def get_task_service() -> TaskService:
    return task_service
