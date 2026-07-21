from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="CRUD api",
    description="Simple CRUD API using FastAPI",
    version="1.0"
)

app.include_router(router)