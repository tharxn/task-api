from fastapi import FastAPI
from app.routes import router
from app.database import initialize_database

app = FastAPI(
    title="Task API",
    description="Task CRUD API using FastAPI and SQLite",
    version="2.0"
)

initialize_database()

app.include_router(router)