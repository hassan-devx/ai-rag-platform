import os
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "fallback-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

security_agent = HTTPBearer()

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generates a secure signed JSON Web Token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=12))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security_agent)):
    """Middleware dependency to protect endpoints from unauthorized access."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Unauthorized architectural scope")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired security token")