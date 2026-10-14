import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.routes import router
from app.service import InvalidTitle, TaskNotFound
from app.auth.client import check_supabase_connection, get_supabase_client, supabase_settings
from app.auth.errors import AuthError
from app.auth.routes import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("uvicorn.error")
    if all(supabase_settings()):
        client = get_supabase_client()
        try:
            next(client)
            await run_in_threadpool(check_supabase_connection)
            logger.info("Server running and connected to Supabase")
        except AuthError:
            logger.warning("Server running; Supabase Auth is currently unavailable")
        finally:
            client.close()
    else:
        logger.warning("Supabase Auth is not configured; set SUPABASE_URL and SUPABASE_KEY")
    yield

app = FastAPI(
    title="Task API",
    description="Task CRUD with PostgreSQL and Supabase authentication",
    version="3.0",
    lifespan=lifespan,
)


@app.exception_handler(AuthError)
def auth_error(request: Request, exc: AuthError):
    headers = {"Cache-Control": "no-store"}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=exc.status_code, content={"error": exc.message}, headers=headers
    )


@app.exception_handler(TaskNotFound)
def task_not_found(request: Request, exc: TaskNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidTitle)
def invalid_title(request: Request, exc: InvalidTitle):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)
app.include_router(auth_router)
