from fastapi import FastAPI
from app.db import init_db
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import auth, documents, admin, chat
from fastapi import FastAPI, HTTPException
from app.db import fetch_all_conversations, fetch_full_chat_history, init_db

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()


# Import your chat router
from app.routers.chat import router as chat_router  # adjust import path if needed

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Hybrid RAG Platform API",
    description="Multi-agent routing backend with local RAG and live web lookups",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount the modular router
app.include_router(chat_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/conversations")
def get_conversations():
    """Returns the list of all past chat sessions for the sidebar."""
    return fetch_all_conversations()

@app.get("/conversations/{session_id}")
def get_conversation_history(session_id: str):
    """Returns all messages belonging to a given session_id."""
    history = fetch_full_chat_history(session_id)
    return {"session_id": session_id, "messages": history}


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Aggregate Modular Sub-Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(chat.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)