from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.pipeline import pipeline
from app.tools import AVAILABLE_TOOLS, MAP_TOOLS
from openai import OpenAI
import os
import json
from app.auth import create_access_token, verify_token, ADMIN_PASSWORD

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
     title="TheImageBuilder Core AI Engine",
     description="Multi-agent routing backend with local RAG and live web lookups",
     version="1.0.0"
)


# Add CORS Middleware so your Next.js application can interact with your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow communication from any origin port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = pipeline

class LoginRequest(BaseModel):
    password: str

# 1. Public Authentication Route (Exchange password for a secure JWT Token)
@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid administrative password")
    
    token = create_access_token(data={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}

# 2. Protected Ingestion Route (Requires valid token dependency to trigger ChromaDB changes)
@app.post("/api/admin/ingest", dependencies=[Depends(verify_token)])
async def ingest_data(data: dict):
    # Your existing vector chunking/ingestion logic lives here safely!
    return {"status": "success", "message": "Context securely chunked and embedded."}

# 3. Protected Chat Route (Requires valid token dependency to protect OpenAI balance)
@app.post("/api/chat/stream", dependencies=[Depends(verify_token)])
async def stream_chat(query: dict):
    # Your existing multi-routing agent logic lives here safely!
    return {"status": "streaming"}




class DocumentPayload(BaseModel):
    document_id: str
    text: str
    metadata: dict = None

class QueryPayload(BaseModel):
    prompt: str

@app.post("/ingest")
async def ingest_document(payload: DocumentPayload):
    try:
        result = pipeline.ingest_document(
            document_id=payload.document_id,
            raw_text=payload.text,
            metadata=payload.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_context(payload: QueryPayload):
    try:
        context_chunks = pipeline.query_similar_context(query=payload.prompt)
        return {"relevant_context": context_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



from typing import Optional
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse

# 1. Update the Pydantic schema keys to match the incoming payload
class ChatRequest(BaseModel):
    prompt: str  # ◄── Changed from 'message' to 'prompt' to match your frontend perfectly!
    session_id: Optional[str] = Field(default="default_session")

    class Config:
        extra = "allow"

# 2. Update the chat route to process the synchronized fields
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Pass request.prompt down into your RAG pipeline streaming engine
    return StreamingResponse(
        pipeline.generate_rag_response(query=request.prompt, session_id=request.session_id),
        media_type="text/event-stream"
    )
   


async def generate_rag_response(self, query: str):
        try:
            # 1. Trigger the "routing" badge on the frontend instantly
            yield "X-STATUS:routing\n"
            await asyncio.sleep(0.4)  # Give the UI a moment to show the clean transition
            
            # --- YOUR AGENT ROUTING LOGIC ---
            # Determine if we need local vector data or live web search
            is_live_search = "latest" in query.lower() or "news" in query.lower() # (or your router logic)

            if is_live_search:
                # 2a. Trigger the Live Web Badge
                yield "X-STATUS:live_web_search\n"
                
                # Execute your DuckDuckGo search logic here...
                context = "Live search results..." 
            else:
                # 2b. Trigger the ChromaDB Local Vector Store Badge
                yield "X-STATUS:local_knowledge_search\n"
                
                # Execute your local ChromaDB query logic here...
                # results = self.collection.query(query_texts=[query], n_results=3)
                context = "Local vector cache content..."

            # 3. Trigger the Synthesizing Badge right before calling OpenAI
            yield "X-STATUS:synthesizing\n"
            await asyncio.sleep(0.3)

            # 4. Stream the actual OpenAI response tokens to the human dialogue box
            # For example, if using openai streaming:
            # response = self.ai_client.chat.completions.create(..., stream=True)
            # for chunk in response:
            #     if chunk.choices[0].delta.content:
            #         yield chunk.choices[0].delta.content

            yield f"Here is the synthesized answer based on the retrieved data: {context}"

        except Exception as e:
            yield f"X-STATUS:error\n"
            yield f"Error processing pipeline: {str(e)}"



@app.post("/agent")
async def run_agent_loop(payload: QueryPayload):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Step 1: Send the user prompt and the list of available tools to the LLM
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an autonomous AI Agent. Use your available tools to answer the query accurately. If you call a tool, use its output to formulate your final response."},
                {"role": "user", "content": payload.prompt}
            ],
            tools=AVAILABLE_TOOLS,
            tool_choice="auto" # The model automatically decides if a tool is needed
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # Step 2: Check if the model decided it needs to use a tool
        if tool_calls:
            messages = [
                {"role": "user", "content": payload.prompt},
                response_message
            ]
            
            # Execute the chosen tools
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Fetch our real Python function from the map and execute it
                run_function = MAP_TOOLS[function_name]
                tool_output = run_function(query=function_args.get("query"))
                
                # Append the tool result to the conversation message history
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_output
                })
                
            # Step 3: Send everything back to OpenAI to compile the final grounded answer
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
            # If the model didn't need any tools, just return its natural response directly
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



# Ensure you import your existing token validation method
# from .auth import verify_token 

@app.post("/api/admin/ingest-file") # ◄── Clean decorator without the dependencies=[] parameter
async def ingest_file_stream(
    file: UploadFile = File(...), 
    current_user: dict = Depends(verify_token) # ◄── Injected right here instead!
):
    try:
        extension = file.filename.split(".")[-1].lower()
        if extension not in ["txt", "md"]:
            raise HTTPException(status_code=400, detail="Unsupported extension layer.")

        file_bytes = await file.read()
        raw_text = file_bytes.decode("utf-8")

        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Document appears empty.")

        # Stream text blocks directly to your pipeline
        pipeline.add_to_vector_store(text_content=raw_text, source=file.filename)
        
        return {
            "status": "success",
            "filename": file.filename,
            "message": "Content cleanly extracted and vectorized dynamically."
        }
    except Exception as e:
        # This will catch the error and print it to your uvicorn terminal console!
        import traceback
        print("Detailed Ingestion Error Traceback:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Core file execution crash: {str(e)}")




@app.post("/api/admin/reset-index", dependencies=[Depends(verify_token)])
async def reset_knowledge_index():
    """Completely wipes out the local ChromaDB collection entries to clear agent memory."""
    try:
        import chromadb
        
        # Connect to local storage
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Delete the collection entirely
        try:
            chroma_client.delete_collection(name="project_knowledge")
        except ValueError:
            # Handle case where collection doesn't exist yet
            pass
            
        # Re-initialize a fresh, clean 1536-dimension instance shell
        chroma_client.get_or_create_collection(
            name="project_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        
        return {
            "status": "success",
            "message": "Persistent vector cache completely flushed. Node index set back to clean baseline."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Index clearing failure: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)