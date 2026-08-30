import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from app.schemas.payloads import DocumentPayload, QueryPayload
from app.pipeline import pipeline

router = APIRouter(tags=["Document Ingestion & Search"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Accepts document uploads, streams to staging disk, and triggers heavy chunking."""
    allowed_extensions = {"txt", "md", "markdown", "py", "pdf", "json", "doc"}
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type .{file_ext}. Please upload code source, markdown files, or text manuals."
        )

    safe_filename = os.path.basename(file.filename)
    target_file_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(target_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file asset to server disk: {str(e)}")
    finally:
        file.file.close()

    try:
        pipeline.ingest_heavy_document(file_path=target_file_path, file_name=safe_filename)
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
        if os.path.exists(target_file_path):
            os.remove(target_file_path)
        raise HTTPException(status_code=500, detail=f"RAG Matrix Ingestion Error: {str(e)}")

@router.post("/ingest")
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

@router.post("/search")
async def search_context(payload: QueryPayload):
    try:
        context_chunks = pipeline.query_similar_context(query=payload.prompt)
        return {"relevant_context": context_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))