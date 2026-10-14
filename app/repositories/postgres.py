from psycopg2.extras import RealDictCursor

from app.database import get_connection
from app.repository import Task


class PostgresTaskRepository:
    def __init__(self, database_url: str | None = None):
        self._database_url = database_url

    def list(self) -> list[Task]:
        with get_connection(self._database_url) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT id, title, done FROM tasks ORDER BY id")
                return [Task(**row) for row in cursor.fetchall()]

    def get(self, task_id: int) -> Task | None:
        with get_connection(self._database_url) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
                )
                row = cursor.fetchone()
                return Task(**row) if row is not None else None

    def create(self, title: str) -> Task:
        with get_connection(self._database_url) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "INSERT INTO tasks (title) VALUES (%s) RETURNING id, title, done",
                    (title,),
                )
                return Task(**cursor.fetchone())

    def update(
        self, task_id: int, title: str | None, done: bool | None
    ) -> Task | None:
        with get_connection(self._database_url) as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    UPDATE tasks
                    SET title = COALESCE(%s, title), done = COALESCE(%s, done)
                    WHERE id = %s
                    RETURNING id, title, done
                    """,
                    (title, done, task_id),
                )
                row = cursor.fetchone()
                return Task(**row) if row is not None else None

    def delete(self, task_id: int) -> bool:
        with get_connection(self._database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                return cursor.rowcount == 1
