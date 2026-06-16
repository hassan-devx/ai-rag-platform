
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.pipeline import pipeline
from app.tools import AVAILABLE_TOOLS, MAP_TOOLS
from openai import OpenAI
import os
import json
from app.auth import create_access_token, verify_token, ADMIN_PASSWORD
import shutil
import time
import asyncio
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts files from the frontend application, streams them securely to disk staging, 
    and passes the file references to the advanced heavy document ingestion pipeline.
    """
    # 1. Basic Extension Check to keep your parsing router happy
    allowed_extensions = {"txt", "md", "markdown", "py", "pdf", "json", "doc"}
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type .{file_ext}. Please upload code source, markdown files, or text manuals."
        )

    # 2. Build local landing destination path
    safe_filename = os.path.basename(file.filename)
    target_file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        # 3. Stream the raw uploaded file directly to disk storage (prevents RAM bloat)
        with open(target_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file asset to server disk: {str(e)}")
    finally:
        file.file.close()  # Always clear the internal file pointer handle

    try:
        # 4. Trigger your specialized multi-index text engine chunking loop!
        pipeline.ingest_heavy_document(file_path=target_file_path, file_name=safe_filename)
        
        # 5. Clean up the temporary staging file from disk to keep the project clean
        if os.path.exists(target_file_path):
            os.remove(target_file_path)
            
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Successfully ingested and synced '{safe_filename}' into the hybrid RAG matrix."
            }
        )
        
    except Exception as e:
        # Clean up files if processing throws an error mid-way
        if os.path.exists(target_file_path):
            os.remove(target_file_path)
        raise HTTPException(status_code=500, detail=f"RAG Matrix Ingestion Error: {str(e)}")


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


class ChatPayload(BaseModel):
    prompt: str
    session_id: str

@app.post("/chat")
def chat_endpoint(payload: ChatPayload):
    user_query = payload.prompt
    session = payload.session_id
    
    print(f"Validated JSON payload successfully! Query: {user_query}")

    def response_generator():
        try:
            # 💡 Call your master orchestration generator function
            raw_stream = pipeline.generate_rag_response(user_query, session_id=session)
            
            for sse_chunk in raw_stream:
                # sse_chunk looks like: 'data: {"text": "hello"}\n\n'
                # Let's clean it up or forward it safely:
                if sse_chunk.startswith("data: "):
                    try:
                        # Extract the raw JSON string out of the data line
                        json_str = sse_chunk.replace("data: ", "").strip()
                        data_dict = json.loads(json_str)
                        text_token = data_dict.get("text", "")
                        
                        if text_token:
                            yield text_token
                    except Exception as parse_err:
                        # If a non-JSON chunk passes through, yield it directly
                        yield sse_chunk
                        
        except Exception as e:
            error_msg = f"Pipeline execution error: {str(e)}"
            print(f"🚨 {error_msg}")
            yield f"X-STATUS:error {error_msg}"

    return StreamingResponse(response_generator(), media_type="text/plain")
   

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


async def response_generator():
        try:
            # Execute your system query handler
            response_text = pipeline.get_response(user_query, session_id=session)
            
            # 💡 PRINT THIS TO TERMINAL TO SEE THE RAW VALUE BEHIND THE NULL:
            print(f"🚨 RAW PIPELINE OUTPUT: Value={response_text} | Type={type(response_text)}")
            
            if response_text is None:
                yield "Error: Pipeline returned Python None."
            else:
                yield f"{response_text}"
                
        except Exception as e:
            print(f"Pipeline processing execution error: {str(e)}")
            yield f"X-STATUS:error Ingestion Pipeline Error: {str(e)}"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)