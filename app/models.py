from typing import Optional
from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[str] = None