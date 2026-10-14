from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import router
from app.service import InvalidTitle, TaskNotFound

app = FastAPI(
    title="Task API",
    description="Task CRUD API using FastAPI and PostgreSQL",
    version="2.0",
)


@app.exception_handler(TaskNotFound)
def task_not_found(request: Request, exc: TaskNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidTitle)
def invalid_title(request: Request, exc: InvalidTitle):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)
