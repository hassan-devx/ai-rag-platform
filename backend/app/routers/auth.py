from fastapi import APIRouter, HTTPException
from app.schemas.payloads import LoginRequest
from app.auth import create_access_token, ADMIN_PASSWORD

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login")
async def login(payload: LoginRequest):
    """Exchanges valid administrative password for a JWT bearer token."""
    if payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid administrative password")
    
    token = create_access_token(data={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}