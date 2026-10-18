"""app.py - FastAPI server. Run: uvicorn app:app --reload  then open http://127.0.0.1:8000/docs"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

import database as db
import pipeline
from seed import seed


class IncomingMessage(BaseModel):
    message: str = Field(min_length=1)
    member_id: int | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()          # make sure tables and sample data exist when the server starts
    yield


app = FastAPI(title="BookLeaf Simple", lifespan=lifespan)


@app.get("/")
def root():
    return {"service": "BookLeaf Simple", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/message")
def message(data: IncomingMessage):
    # Plain def: FastAPI runs it in a worker thread, and a SQLite connection must be
    # used in the thread that made it, so we open one connection per request.
    conn = db.connect()
    try:
        return pipeline.run_pipeline(conn, data.message, data.member_id)
    finally:
        conn.close()


@app.get("/tasks")
def tasks():
    """Escalations waiting for a librarian."""
    conn = db.connect()
    try:
        return [dict(t) for t in db.list_tasks(conn)]
    finally:
        conn.close()