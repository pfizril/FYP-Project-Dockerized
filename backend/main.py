from typing import Union, List, Annotated
from pydantic import BaseModel 
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import models
from models import EndpointHealth, APIEndpoint, APIRequest, RemoteServer
from database import engine, session, get_db, get_db_session
from sqlalchemy.orm import Session
from datetime import datetime
import auth
import csrf_protection
import api_management
import security
import api_analytics
import remote_server_api
from starlette import status 
from auth import get_current_user, role_required, check_endpoint_status
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from api_analytics import check_endpoint_health
import asyncio
import logging
from urllib.parse import parse_qs
import time
from security_headersmiddleware import SecurityHeadersMiddleware
from security import SecurityMiddleware, detect_sql_injection, validate_and_normalize_url
from security import EnhancedThreatDetection
import os
from remote_server_service import RemoteServerService
from background_tasks import start_background_tasks
from api_discovery_service import APIDiscoveryService
from models import DiscoveredEndpoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# initialize enhance security
enhanced_security = EnhancedThreatDetection(session())

# Monitoring loop 
async def lifespan(app: FastAPI):
    db = session() 
    try:
        yield  
    finally:
        # task.cancel()  
        db.close()  

async def log_event(db: Session, message: str, level: str = "INFO"):
    logging.log(getattr(logging, level.upper()), message)



# Create FastAPI app with lifespan
app = FastAPI(
    title="API Security System",
    description="API Security and Monitoring System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure async support
app.state.async_mode = True

# Include routers
app.include_router(auth.router)
app.include_router(api_management.router)
app.include_router(security.router)
app.include_router(api_analytics.router)
app.include_router(csrf_protection.router)
app.include_router(remote_server_api.router)

# Add security middleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


# Create database tables
models.Base.metadata.create_all(bind=engine)

# Pydantic models and database dependency
class UsersBase(BaseModel):
    user_id: int
    user_name: str
    user_role: str
    user_email: str
    user_psw: str

class EndpointBaseDisplay(BaseModel):
    name: str
    url: str
    method: str
    status: bool
    description: str

class UpdateEndpointBase(BaseModel):
    name: str = None
    url: str = None
    method: str = None
    status: bool = None
    updated_at: datetime = None

class Config:
    orm_mode = True

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()

db_dependecy = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# CORS configuration
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:5173", 
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],
)

@app.middleware("http")
async def block_down_endpoints(request: Request, call_next):
    # Check if it's a health check request
    is_health_check = request.headers.get("X-Health-Check") == "true"
    health_check_api_key = os.getenv("HEALTH_CHECK_API_KEY", "health-monitor-key")
    provided_api_key = request.headers.get("X-API-KEY")
    
    # If it's a health check with the correct API key, allow it
    if is_health_check and provided_api_key == health_check_api_key:
        return await call_next(request)
    
    # Otherwise, use the regular check_endpoint_status
    return await check_endpoint_status(request, call_next)

# Create a dedicated health check endpoint that doesn't require authentication
@app.get("/health")
def health_check():
    """
    Public health check endpoint - doesn't require authentication
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    }

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Normalize and validate URL
    normalized_url = validate_and_normalize_url(str(request.url))
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log request details
    db = session()
    log_entry = APIRequest(
        timestamp=datetime.now(),
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code,
        response_time=process_time,
        client_ip=request.client.host
    )
    
    try:
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logging.error(f"Failed to log request: {e}")
        db.rollback()
    finally:
        db.close()

    return response

# Root endpoint
@app.get("/")
def read_root():
    return {"Hello": "API Security System"}

# Admin dashboard with RBAC
@app.get("/admin-dashboard")
@role_required(["Admin"])
def admin_dashboard(user: user_dependency):
    return {"message": f"Welcome, {user.get('username')}. You have admin access."}

# Test payload endpoint with additional security checks
@app.post("/test-payload")
async def test_payload(data: dict):
    # Additional security checks can be added here if needed
    return {"message": "Payload received successfully"}

# Start background tasks
@app.on_event("startup")
async def startup_event():
    start_background_tasks()

@app.get("/dashboard/remote/{server_id}")
async def get_remote_dashboard(server_id: int, db: Session = Depends(get_db)):
    """Get dashboard data for a specific remote server"""
    service = RemoteServerService(db)
    
    # Get server details
    server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
        
    # Get endpoints and metrics
    endpoints = await service.get_server_endpoints(server_id)
    metrics = await service.get_server_metrics(server_id)
    
    return {
        "server": {
            "id": server.id,
            "name": server.name,
            "base_url": server.base_url,
            "status": server.status,
            "last_checked": server.last_checked
        },
        "endpoints": endpoints,
        "metrics": metrics
    }

@app.post("/api/remote-servers/{server_id}/discover")
async def discover_endpoints(server_id: int, db: Session = Depends(get_db)):
    try:
        server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        discovery_service = APIDiscoveryService(db, server)
        endpoints = await discovery_service.discover_endpoints()
        await discovery_service.store_discovered_endpoints(endpoints)
        
        return {"message": f"Successfully discovered {len(endpoints)} endpoints"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/remote-servers/{server_id}/discovered-endpoints/count")
async def get_discovered_endpoints_count(server_id: int, db: Session = Depends(get_db)):
    try:
        count = db.query(DiscoveredEndpoint).filter(
            DiscoveredEndpoint.remote_server_id == server_id,
            DiscoveredEndpoint.is_active == True
        ).count()
        
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

