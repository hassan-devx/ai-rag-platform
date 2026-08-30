from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class LoginRequest(BaseModel):
    password: str

class DocumentPayload(BaseModel):
    document_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

class QueryPayload(BaseModel):
    prompt: str

class ChatPayload(BaseModel):
    prompt: str
    session_id: Optional[str] = "default"
    chat_history: Optional[List[Dict[str, str]]] = []  # 👈 Added conversation history