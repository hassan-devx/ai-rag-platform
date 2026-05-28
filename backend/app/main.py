from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.pipeline import RAGPipeline
from app.tools import AVAILABLE_TOOLS, MAP_TOOLS
from openai import OpenAI
import os
import json


app = FastAPI(title="Enterprise AI RAG Engine")

# Add CORS Middleware so your Next.js application can interact with your backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow communication from any origin port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = RAGPipeline()

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

@app.post("/chat")
async def chat_stream(payload: QueryPayload):
    try:
        # We return a StreamingResponse which takes our Python generator method
        return StreamingResponse(
            pipeline.generate_rag_response(query=payload.prompt),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)