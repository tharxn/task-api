# Task API

A CRUD REST API built with FastAPI and PostgreSQL. Docker Compose starts the app and database together. Tasks are stored in a named Docker volume and survive app and database container restarts.

## Start the whole stack

Install and start Docker Desktop (Linux containers), then clone the project:

```bash
git clone https://github.com/tharxn/task-api.git
cd task-api
```

Create the local configuration once.

**PowerShell:**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

The example contains matching local development credentials:

```dotenv
POSTGRES_DB=taskdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST_PORT=5433
DATABASE_URL=postgresql://postgres:postgres@db:5432/taskdb
```

Keep the database name, username, and password consistent with `DATABASE_URL`. Percent-encode special characters in the URL credentials. Inside Compose, the database hostname is `db`. The app reads the connection string from `DATABASE_URL`; the `POSTGRES_*` variables initialize the database container. The real `.env` is gitignored and excluded from the app image. Only `.env.example` belongs in Git.

Start both services with one command:

```bash
docker compose up
```

The first run builds the app image and downloads Postgres. Compose waits for the database healthcheck before starting the app. The app healthcheck also reads `/tasks`, checking that the API can query its database.

- API: [http://localhost:8000](http://localhost:8000)
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

For a background run that waits for readiness:

```bash
docker compose up --build -d --wait
docker compose ps
```

Rebuild with `--build` after changing Python code or dependencies.

## Database and SQL

Postgres 16 stores its data in the `postgres_data` named volume, mounted at `/var/lib/postgresql/data`. Compose normally names it `task-api_postgres_data`.

The database container executes `app/init.sql` on its first start with an empty volume. It creates:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(btrim(title)) > 0),
    done BOOLEAN NOT NULL DEFAULT FALSE
);
```

There are no automatic sample rows. Create tasks through the API. The old `tasks.db` and SQLite screenshots are historical artifacts; the running app uses PostgreSQL and does not migrate that SQLite file.

Initialization scripts run only for an empty volume. For an existing database that needs the table, apply the same file without deleting its data:

```bash
docker compose exec db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/01-init.sql'
```

Changing `POSTGRES_USER`, `POSTGRES_PASSWORD`, or `POSTGRES_DB` in `.env` does not change an already initialized database. Use matching credentials or update the database explicitly.

## Repository and service layers

Requests follow this path:

```text
routes.py -> TaskService -> TaskRepository
                               |-- InMemoryTaskRepository
                               |-- PostgresTaskRepository (selected)
```

The shared interface in `app/repository.py` defines `list`, `get`, `create`, `update`, and `delete`. The service validates task titles and handles missing tasks. The routes handle HTTP. SQL, transactions, and connection cleanup belong to the Postgres repository and connection helper.

**Honest migration note:** the starting checkout had SQL directly in routes, an unfinished SQLite-to-Postgres migration, and no separate A2 service or repository interface. Completing this task required refactoring those routes and adding a service first. It would be inaccurate to claim the original service and routes were unchanged. The existing endpoint paths, response fields, and success status codes are preserved; `done` is now correctly a boolean.

With these layers established, **switching between the two repository implementations leaves the service and routes unchanged**. Only `app/dependencies.py` selects storage. Its default is:

```python
from app.repositories.postgres import PostgresTaskRepository
from app.service import TaskService

task_service = TaskService(PostgresTaskRepository())
```

To use memory, change the import and constructor in that same file to `InMemoryTaskRepository` from `app.repositories.memory`. Memory is for development/tests and loses data on restart. Both implementations run the same service contract tests.

## API endpoints

| Method | Endpoint | Result |
| --- | --- | --- |
| GET | `/` | API information |
| GET | `/health` | Process liveness |
| GET | `/tasks` | All tasks, ordered by ID |
| GET | `/tasks/{task_id}` | One task, or 404 |
| POST | `/tasks` | Create a task; 201 |
| PUT | `/tasks/{task_id}` | Update supplied fields, or 404 |
| DELETE | `/tasks/{task_id}` | Delete a task; 204, or 404 |

Create a task in PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/tasks -Method Post -ContentType 'application/json' -Body '{"title":"Buy Milk"}'
```

Or with curl:

```bash
curl -X POST http://localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title":"Buy Milk"}'
```

A task has the shape `{"id":1,"title":"Buy Milk","done":false}`. Update its completion with `{"done":true}`. Omitted or null update fields retain their existing values. Blank titles return 400; invalid request types return 422.

## Prove persistence

With the stack running, execute the verification script using Python 3.12 or newer:

```bash
python scripts/verify_stack.py
```

The script uses only Python's standard library. It creates two uniquely named rows through HTTP, updates one, and checks CRUD, validation, and missing-task responses. It then:

1. Runs `docker compose restart app db`.
2. Reads both rows again and compares IDs, titles, and boolean values.
3. Runs `docker compose up -d --force-recreate --wait --wait-timeout 120`.
4. Verifies that both container IDs changed and that the same rows still exist.

It leaves the two proof rows in Postgres for inspection. It restarts this project's stack, so run it when no other request is in progress.

Verified locally on **14 October 2026**, using the real `.env` and Docker Compose stack:

| Check | Result |
| --- | --- |
| Shared memory/Postgres contract suite | 15 tests passed, no skips |
| HTTP CRUD, validation, and missing-task responses | Passed |
| After `docker compose restart app db` | Rows 9 and 10 retained the same IDs, titles, and `done` values |
| After recreating both containers | Both container IDs changed; the same two rows remained |
| SQL inspection in the database container | Both proof rows present |
| Local `.env` file inside the app image | Absent |

The retained proof rows are:

```json
[
  {"id":9,"title":"persistence-30a9dae0-7ddb-4313-9e70-c7c9d0d9b988-one","done":true},
  {"id":10,"title":"persistence-30a9dae0-7ddb-4313-9e70-c7c9d0d9b988-two","done":false}
]
```

The script finished with `PASS: HTTP CRUD and persistence; both container IDs changed.` IDs will differ on later runs.

Stop and remove containers while keeping tasks:

```bash
docker compose down
docker compose up -d --wait
```

The named volume survives `down`. Adding `-v` removes the database volume and its rows.

## Tests

Run the shared contract tests against memory and the live Postgres database:

```bash
docker compose exec -e RUN_POSTGRES_TESTS=1 app python -m unittest discover -v
```

The tests create their own rows and clean up those rows without clearing existing tasks. They cover CRUD, ordering, partial updates, `done=false`, missing IDs, blank-title validation, SQL punctuation/Unicode, and committed reads from a new repository instance.

For memory tests without Docker:

```bash
python -m venv venv
# Activate venv, then:
pip install -r requirements.txt
python -m unittest discover -v
```

The eight Postgres tests are skipped unless `RUN_POSTGRES_TESTS=1`.

## Run the app outside Docker

Start just the database with `docker compose up -d db`. Install `requirements.txt` in a virtual environment, then point the host app at `localhost` instead of `db`.

**PowerShell** (adjust credentials to match `.env`):

```powershell
$env:DATABASE_URL = 'postgresql://postgres:postgres@localhost:5433/taskdb'
uvicorn app.main:app --reload
```

**Linux / macOS:**

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/taskdb uvicorn app.main:app --reload
```

The connection helper loads the project-root `.env` without overriding an existing environment variable. The database is published on local port 5433 by default to avoid conflicts with an existing Postgres installation. Set `POSTGRES_HOST_PORT` in `.env` to change it; the container connection string always uses `db:5432`.

## Project structure

```text
app/
  main.py                  FastAPI app and HTTP error handlers
  routes.py                HTTP endpoints
  models.py                Request models
  service.py               Task rules
  repository.py            Shared repository interface
  dependencies.py          Storage selection
  database.py              DATABASE_URL and transaction/connection lifecycle
  repositories/
    memory.py              In-memory implementation
    postgres.py            PostgreSQL implementation
  init.sql                 Table definition
scripts/verify_stack.py    HTTP CRUD and restart/recreation proof
tests/                     Shared repository/service tests
docker-compose.yml         App, Postgres, healthchecks, named volume
Dockerfile                 Python app image
.env.example               Committed local configuration example
```

## References

- [Docker Compose startup and readiness](https://docs.docker.com/compose/how-tos/startup-order/)
- [Official Postgres image and initialization scripts](https://hub.docker.com/_/postgres)
- [Psycopg transactions and parameterized SQL](https://www.psycopg.org/docs/usage.html)

## Author

**Tharun Kumar**
