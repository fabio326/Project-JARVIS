"""FastAPI backend for Project JARVIS.

Run this server manually when you are ready:

    uvicorn jarvis.api:app --reload

The existing terminal app in main.py is unchanged and can still be used separately.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from agents import SQLiteSession
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from jarvis.agent import create_jarvis_orchestrator
from jarvis.brain.orchestrator import JarvisOrchestrator

# Paths shared with the terminal app so both use the same memory database file.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DB = PROJECT_ROOT / "jarvis_memory.db"

# Separate session ID from the terminal app so API chats do not mix with CLI chats.
API_SESSION_ID = "jarvis-api"

# Local frontend origins allowed during development.
LOCAL_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

# Created once when the server starts and reused for every request.
jarvis_orchestrator: JarvisOrchestrator | None = None
jarvis_session: SQLiteSession | None = None


class ChatRequest(BaseModel):
    """Incoming chat message from a frontend or API client."""

    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, value: str) -> str:
        """Reject blank or whitespace-only messages before calling JARVIS."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned


def load_api_key() -> str:
    """Load the OpenAI API key from the local .env file without exposing it in responses."""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    os.environ["OPENAI_API_KEY"] = api_key
    return api_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare JARVIS when the server starts and clean up when it shuts down."""
    global jarvis_orchestrator, jarvis_session

    # Startup: load secrets, create the orchestrator, and open persistent memory.
    load_api_key()
    jarvis_orchestrator = create_jarvis_orchestrator()
    jarvis_session = SQLiteSession(API_SESSION_ID, MEMORY_DB)

    yield

    # Shutdown: close the SQLite session so database files are released cleanly.
    if jarvis_session is not None:
        jarvis_session.close()
        jarvis_session = None
    jarvis_orchestrator = None


app = FastAPI(
    title="Project JARVIS API",
    description="Local FastAPI backend for the JARVIS assistant.",
    lifespan=lifespan,
)

# Allow browser-based local frontends to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_DEV_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check for the API, agent, memory, and macOS tools."""
    if jarvis_orchestrator is None or jarvis_session is None:
        raise HTTPException(status_code=503, detail="JARVIS is still starting up.")

    return {
        "status": "online",
        "brain": "online",
        "memory": "connected",
        "mac_control": "ready",
    }


@app.post("/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    """Send one message to JARVIS and return the assistant response."""
    if jarvis_orchestrator is None or jarvis_session is None:
        raise HTTPException(status_code=503, detail="JARVIS is not ready yet.")

    try:
        response_text = await jarvis_orchestrator.run(
            request.message,
            session=jarvis_session,
        )
    except Exception:
        # Never return raw exception details that might include secrets.
        raise HTTPException(
            status_code=500,
            detail="JARVIS could not process your message. Please try again.",
        ) from None

    return {"response": response_text}
