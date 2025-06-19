from fastapi import Depends, HTTPException, Request, Response, status, APIRouter
from fastapi.security import APIKeyCookie
from pydantic import BaseModel
from sqlalchemy.orm import Session
import secrets
from typing import Optional
import logging

# Define CSRF token models
class CSRFToken(BaseModel):
    csrf_token: str

router = APIRouter(
    prefix='/csrf',
    tags=['CSRF Protection']
)

# Initialize the CSRF cookie dependency
csrf_cookie = APIKeyCookie(name="csrf_token", auto_error=False)

def generate_csrf_token():
    """Generate a new CSRF token"""
    return secrets.token_hex(32)

async def csrf_protect(
    request: Request,
    csrf_token: Optional[str] = Depends(csrf_cookie),
    db: Session = None
):
    """
    Validate CSRF token for all non-GET, non-HEAD, non-OPTIONS requests
    This is used for individual route protection when not using the unified middleware
    """
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return True
    
    # For API requests, check header
    header_token = request.headers.get("X-CSRF-Token")
    
    # No token in cookie or header
    if not csrf_token and not header_token:
        logging.warning(f"CSRF token missing in request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing"
        )
    
    # If token is in header, it must match the cookie
    if header_token and csrf_token and header_token != csrf_token:
        logging.warning(f"CSRF token mismatch in request from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="CSRF token validation failed"
        )
    
    return True

# Endpoint for getting a new token
@router.get("/csrf-token", response_model=CSRFToken)
async def get_csrf_token(response: Response):
    token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Need to be accessible from JavaScript
        secure=True,     # Only sent over HTTPS
        samesite="strict" # Protection against CSRF
    )
    return {"csrf_token": token}

# Test endpoint for CSRF protection
@router.post("/test-csrf-protection")
async def test_csrf_protection(request: Request):
    # This endpoint is automatically protected by our unified security middleware
    # It will check for CSRF token, JWT/API key
    return {"message": "CSRF protection working"}