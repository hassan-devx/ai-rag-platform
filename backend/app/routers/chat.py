import os
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import OpenAI
from app.schemas.payloads import ChatPayload, QueryPayload
from app.pipeline import pipeline
from app.auth import verify_token
from app.tools import AVAILABLE_TOOLS, MAP_TOOLS
from typing import List, Optional
from pydantic import BaseModel

from app.db import get_db, fetch_conversation_history
from slowapi import Limiter
from slowapi.util import get_remote_address



# Use the same key_func or import limiter instance
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

class ChatRequest(BaseModel):
    prompt: str
    session_id: str
    chat_history: Optional[List[dict]] = []

@router.post("/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, payload: ChatRequest):
    return StreamingResponse(
        pipeline.generate_rag_response(
            query=payload.prompt,
            session_id=payload.session_id,
            chat_history=payload.chat_history
        ),
        media_type="text/event-stream"
    )


@router.get("/conversations")
async def list_conversations():
    """Returns list of session titles for sidebar."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT session_id, title, created_at FROM conversations ORDER BY created_at DESC;")
        rows = cur.fetchall()
    conn.close()
    return rows

@router.get("/conversations/{session_id}")
async def get_conversation_messages(session_id: str):
    """Loads full message history when a user clicks a title."""
    return fetch_conversation_history(session_id, limit=50)




@router.post("/api/chat/stream", dependencies=[Depends(verify_token)])
async def stream_chat(query: dict):
    """Protected streaming route requiring JWT verification."""
    return {"status": "streaming"}

@router.post("/agent")
async def run_agent_loop(payload: QueryPayload):
    """
    Autonomous AI Agent loop using OpenAI function calling to selectively 
    invoke tools (e.g., local RAG vs. live web search).
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Step 1: Query the model with registered tools
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an autonomous AI Agent. Use your available tools to answer the query accurately. If you call a tool, use its output to formulate your final response."},
                {"role": "user", "content": payload.prompt}
            ],
            tools=AVAILABLE_TOOLS,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Step 2: Execute tool functions if requested by model
        if tool_calls:
            messages = [
                {"role": "user", "content": payload.prompt},
                response_message
            ]
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                run_function = MAP_TOOLS[function_name]
                tool_output = run_function(query=function_args.get("query"))
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output
                })
                
            # Step 3: Stream back final synthesized completion
            final_stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )
            
            def stream_generator():
                for chunk in final_stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
            return StreamingResponse(stream_generator(), media_type="text/plain")
            
        else:
            # Fallback direct response if no tool execution was required
            return StreamingResponse(
                (chunk.choices[0].delta.content for chunk in client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": payload.prompt}],
                    stream=True
                ) if chunk.choices[0].delta.content),
                media_type="text/plain"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))