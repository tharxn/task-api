# Task API: Supabase Auth and PostgreSQL

A FastAPI project with Supabase signup, login, logout, and bearer-protected user endpoints, alongside persistent task CRUD in PostgreSQL. Docker Compose starts the app and database together.

## Supabase Auth: setup and test

The auth assignment adds signup, login, logout, and two user-only routes to the existing Postgres project. Supabase manages passwords and issues tokens. The backend verifies bearer tokens with `supabase.auth.get_user(token)` before returning private data.

### 1. Configure a Supabase project

Create a free project in the [Supabase Dashboard](https://supabase.com/dashboard). Open **Connect** to copy the Project URL and publishable key (the legacy anon key also works). In your local `.env`, add:

```dotenv
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-or-publishable-key
PORT=8000
```

These alternative names are also supported:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
```

Use one matching URL/key pair. The `SUPABASE_*` names take precedence if both forms are set. Use a publishable/anon key; this app does not need a service-role or secret key. Keep real values and test passwords in `.env`, which is ignored by Git and excluded from the image.

Email/password authentication must be enabled in the project's Authentication settings. With email confirmation enabled, signup returns a user but login works only after the verification link is clicked. A Supabase **dashboard** account does not automatically become a user in the project's Authentication user list.

### 2. Start the API

After creating `.env` from `.env.example` and filling in Supabase values:

```bash
docker compose up --build -d --wait
```

The API runs on [http://localhost:8000](http://localhost:8000). Successful startup checks the actual Supabase Auth health endpoint and logs `Server running and connected to Supabase`. If Supabase is unavailable, auth fails closed; the existing Postgres API can still start. Missing Supabase settings return 503 from auth operations.

### 3. Try the flow in Swagger

Open [http://localhost:8000/docs](http://localhost:8000/docs).

1. Expand **POST /auth/signup**, click **Try it out**, and submit your email/password. Expect 201 and a `user` object.
2. Confirm the signup email if `confirmation_required` is true. A redirect to a local page that is not running can fail after email verification has already completed.
3. Call **POST /auth/login** with the same credentials. Copy `access_token`; `refresh_token` is also returned.
4. Click **Authorize**, paste only the access token (without the `Bearer` prefix), and authorize.
5. Execute **GET /protected/profile** and **GET /protected/dashboard**. Expect 200.
6. Remove authorization, or change one character in the token's signature. The protected route returns 401.
7. Restore a valid token and execute **POST /auth/logout**. Expect 204 with no response body. Clear tokens from the client afterward.

The lock icons identify routes that require a verified bearer token:

![Swagger UI showing signup, login, logout, and protected routes](screenshots/swagger-auth.jpg)

### Auth API reference

| Method | Endpoint | Auth required | Success |
| --- | --- | --- | --- |
| POST | `/auth/signup` | No | 201; user and confirmation state |
| POST | `/auth/login` | No | 200; access token, refresh token, token type, expiry |
| POST | `/auth/logout` | Bearer JWT | 204; current session signed out |
| GET | `/public/info` | No | 200; public welcome message |
| GET | `/protected/profile` | Bearer JWT | 200; verified user's ID, email, creation time |
| GET | `/protected/dashboard` | Bearer JWT | 200; dashboard message and verified user ID |

Missing/blank email or password returns 400 with `{"error":"Email and password are required"}`. Invalid login returns 401 with `{"error":"Invalid login credentials"}`. Missing or malformed authorization returns 401 with `{"error":"Access token required"}`. Rejected tokens return 401 with `{"error":"Invalid or expired token"}`. Rate limits return 429; an unavailable auth provider returns 503.

The original `/tasks` CRUD routes remain shared and public. This assignment protects `/protected/*` and logout; task ownership and admin-role authorization are not implemented.

### How protection and logout work

Auth routes use a separate Supabase client for each request, with session persistence and automatic refresh disabled. Users cannot inherit another request's SDK session. The shared FastAPI `get_current_user` dependency extracts the bearer token and asks Supabase to validate it. Both profile and dashboard use that same guard. The app never trusts an unverified JWT payload.

Logout verifies the bearer token first, then calls the Python SDK's token-taking `auth.admin.sign_out(token, scope="local")` method. This is the SDK-supported way to sign out a supplied user JWT without storing a server session or requiring a refresh token. The request uses the user's token and the project's publishable key, with no service-role key. Local scope signs out that session.

Supabase revokes the session's refresh token. An issued access JWT can remain valid until expiry, so clients must discard both tokens; logout is not a promise of immediate JWT invalidation for every verifier. See [Supabase's logout documentation](https://supabase.com/docs/reference/python/auth-signout).

### Reproduce the live auth checks

Install `requirements.txt` in a Python virtual environment. Add a test app user's credentials only to your local `.env`:

```dotenv
AUTH_TEST_EMAIL=
AUTH_TEST_PASSWORD=
```

These values are used only by the local verification script and are not passed into the app container.

For a new app user:

```bash
python scripts/verify_auth.py --signup-if-needed
```

If email confirmation is required, click the verification link, then run:

```bash
python scripts/verify_auth.py
```

The script tests public access, missing credentials, login, invalid credentials, valid profile/dashboard access, a tampered signature, missing/invalid tokens, logout, and refresh-token rejection after logout. It does not print passwords or tokens. Set `API_BASE_URL` if testing on a different local port.

**Live verification on 14 October 2026:** signup returned 201; email confirmation was completed; login and both protected routes returned 200; missing/invalid/tampered tokens returned 401; logout returned 204; Supabase rejected the revoked refresh token with 400. The protected profile also returned 401 with the logged-out access token in this run. These were requests to the configured Supabase project, separate from the mocked tests. The same flow passed through the Docker-hosted API. Swagger's login, Authorize dialog, and protected profile were also exercised in the browser, returning 200.

### Assignment commits

The assignment was implemented in order, with separate commits for:

- Stage 0: setup server and supabase client
- Stage 1: signup and login routes working
- Stage 2: public route and unverified protected route
- Stage 3: profile route token verification
- Stage 4: auth middleware and logout endpoint
- Stage 5: Swagger UI documentation with bearer auth
- Stage 6: publish to GitHub and write README

The Stage 2 checkpoint fails closed while verification is not implemented; later stages add real verification. No unverified profile data is returned at that checkpoint.

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

Run the auth tests and shared repository contract tests against memory and the live Postgres database:

Verified in the rebuilt Docker container on 14 October 2026: **35 tests passed, no skips**.

```bash
docker compose exec -e RUN_POSTGRES_TESTS=1 app python -m unittest discover -v
```

The 20 auth/configuration tests use the real Supabase SDK with mocked HTTP responses; they do not contact Supabase or create real users. They cover credentials, headers, token verification, dependency reuse, logout, provider failures, and OpenAPI security. The 15 repository tests cover memory and real PostgreSQL. They create their own rows and clean up those rows without clearing existing tasks, covering CRUD, ordering, partial updates, `done=false`, missing IDs, blank titles, SQL punctuation/Unicode, and committed reads from a new repository instance.

For memory tests without Docker:

```bash
python -m venv venv
# Activate venv, then:
pip install -r requirements.txt
python -m unittest discover -v
```

Without Postgres, 27 tests pass and the eight Postgres tests are skipped unless `RUN_POSTGRES_TESTS=1`.

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
  __main__.py              Server entry point and PORT configuration
  main.py                  FastAPI app, startup check, and HTTP error handlers
  protected_routes.py      Public info, protected profile and dashboard
  auth/                    Supabase client, service, dependency, models, routes
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
scripts/verify_auth.py     Live Supabase signup/login/protection/logout checks
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
