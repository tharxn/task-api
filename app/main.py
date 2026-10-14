import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import router
from app.service import InvalidTitle, TaskNotFound
from app.auth.client import get_supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("uvicorn.error")
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        client = get_supabase_client()
        try:
            next(client)
            logger.info("Server running; Supabase client initialized")
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


@app.exception_handler(TaskNotFound)
def task_not_found(request: Request, exc: TaskNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidTitle)
def invalid_title(request: Request, exc: InvalidTitle):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)
