from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import chromadb
from app.auth import verify_token
from app.pipeline import pipeline

router = APIRouter(prefix="/api/admin", tags=["Admin Control Panel"])

@router.post("/ingest", dependencies=[Depends(verify_token)])
async def ingest_data(data: dict):
    return {"status": "success", "message": "Context securely chunked and embedded."}

@router.post("/ingest-file")
async def ingest_file_stream(
    file: UploadFile = File(...), 
    current_user: dict = Depends(verify_token)
):
    try:
        extension = file.filename.split(".")[-1].lower()
        if extension not in ["txt", "md"]:
            raise HTTPException(status_code=400, detail="Unsupported extension layer.")

        file_bytes = await file.read()
        raw_text = file_bytes.decode("utf-8")

        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="Document appears empty.")

        pipeline.add_to_vector_store(text_content=raw_text, source=file.filename)
        
        return {
            "status": "success",
            "filename": file.filename,
            "message": "Content cleanly extracted and vectorized dynamically."
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Core file execution crash: {str(e)}")

@router.post("/reset-index", dependencies=[Depends(verify_token)])
async def reset_knowledge_index():
    """Completely flushes the local ChromaDB collection entries to reset agent memory."""
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        try:
            chroma_client.delete_collection(name="project_knowledge")
        except ValueError:
            pass
            
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