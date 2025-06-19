from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from database import get_db, get_db_session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
from auth import get_current_user, role_required
from remote_server_service import RemoteServerService
from remote_server_scanner import RemoteServerScanner
from simple_remote_scanner import SimpleRemoteScanner
import logging

# NOTE: All routes in this file are registered under /remote-servers, not /api/remote-servers

router = APIRouter(
    prefix="/remote-servers",
    tags=["remote-servers"]
)

logger = logging.getLogger(__name__)

class RemoteServerBase(BaseModel):
    name: str
    base_url: str
    description: Optional[str] = None
    api_key: Optional[str] = None
    health_check_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    auth_type: Optional[str] = "basic"
    token_endpoint: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class RemoteServerCreate(RemoteServerBase):
    pass

class RemoteServerUpdate(RemoteServerBase):
    is_active: Optional[bool] = None

class RemoteServerResponse(RemoteServerBase):
    id: int
    status: str
    created_at: datetime
    last_checked: Optional[datetime]
    retry_count: int
    last_error: Optional[str]
    updated_at: datetime
    created_by: int
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }

@router.post("/", response_model=RemoteServerResponse)
@role_required(["Admin"])
def create_remote_server(
    server: RemoteServerCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new remote server entry."""
    try:
        logger.info(f"Attempting to create remote server: {server.model_dump()}")
        logger.info(f"Current user: {user}")
        
        # Create server data dictionary
        server_data = server.model_dump()
        server_data["created_by"] = user.get("id")
        server_data["status"] = "active"
        server_data["retry_count"] = 0
        server_data["is_active"] = True
        
        # Create and save the server
        db_server = RemoteServer(**server_data)
        db.add(db_server)
        db.commit()
        db.refresh(db_server)
        
        return db_server
        
    except Exception as e:
        logger.error(f"Unexpected error creating remote server: {str(e)}", exc_info=True)
        if 'db_server' in locals():
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create remote server: {str(e)}"
        )

@router.get("/", response_model=List[RemoteServerResponse])
@role_required(["Admin"])
def list_remote_servers(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all remote servers."""
    try:
        logger.info(f"Listing remote servers for user: {user}")
        servers = list(db.query(RemoteServer).all())
        logger.info(f"Found {len(servers)} remote servers")
        return servers
    except Exception as e:
        logger.error(f"Error listing remote servers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list remote servers: {str(e)}"
        )

@router.get("/{server_id}", response_model=RemoteServerResponse)
@role_required(["Admin"])
async def get_remote_server(
    server_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get details of a specific remote server."""
    server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remote server not found"
        )
    return server

@router.put("/{server_id}", response_model=RemoteServerResponse)
@role_required(["Admin"])
async def update_remote_server(
    server_id: int,
    server_update: RemoteServerUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update a remote server's details."""
    try:
        logger.info(f"=== BACKEND UPDATE SERVER DEBUG ===")
        logger.info(f"Server ID: {server_id}")
        logger.info(f"Current user: {user}")
        logger.info(f"Received data: {server_update.model_dump()}")
        
        db_server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not db_server:
            logger.error(f"Server with ID {server_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remote server not found"
            )

        logger.info(f"Found server: {db_server.name}")
        logger.info(f"Current server data: {db_server.__dict__}")

        update_data = server_update.model_dump(exclude_unset=True)
        logger.info(f"Update data (exclude_unset=True): {update_data}")
        
        for key, value in update_data.items():
            logger.info(f"Setting {key} = {value}")
            setattr(db_server, key, value)

        logger.info("Committing to database...")
        db.commit()
        db.refresh(db_server)
        
        logger.info(f"Updated server data: {db_server.__dict__}")
        logger.info("Update completed successfully")
        
        return db_server
        
    except Exception as e:
        logger.error(f"Error updating server: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update server: {str(e)}"
        )

@router.delete("/{server_id}")
@role_required(["Admin"])
async def delete_remote_server(
    server_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Delete a remote server."""
    try:
        logger.info(f"=== BACKEND DELETE SERVER DEBUG ===")
        logger.info(f"Server ID: {server_id}")
        logger.info(f"Current user: {user}")
        server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            logger.error(f"Server with ID {server_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Remote server not found"
            )
        logger.info(f"Found server: {server.name}")
        logger.info(f"Attempting to delete server...")
        db.delete(server)
        db.commit()
        logger.info(f"Server deleted successfully")
        return {"message": "Remote server deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting server: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete server: {str(e)}"
        )

@router.get("/{server_id}/test-data")
async def get_test_data(
    server_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get test data for the remote server dashboard."""
    try:
        # Check if user has admin role
        if user.get('role') != 'Admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions to access this resource."
            )

        # Get server
        server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        # Get discovered endpoints
        endpoints = db.query(DiscoveredEndpoint).filter(
            DiscoveredEndpoint.remote_server_id == server_id
        ).all()

        # Transform endpoints into a simple format
        endpoint_data = [
            {
                "id": endpoint.id,
                "path": endpoint.path,
                "method": endpoint.method,
                "status": "active",  # Simplified status
                "last_checked": datetime.now().isoformat(),
                "response_time": 100,  # Example response time
                "status_code": 200,  # Example status code
            }
            for endpoint in endpoints
        ]

        return {
            "server": {
                "id": server.id,
                "name": server.name,
                "base_url": server.base_url,
                "status": server.status
            },
            "endpoints": endpoint_data
        }

    except Exception as e:
        logger.error(f"Error getting test data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test data: {str(e)}"
        )

@router.get("/{server_id}/test-dashboard")
async def get_test_dashboard_data(
    server_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get test data for the remote server test dashboard."""
    try:
        # Check if user has admin role
        if user.get('role') != 'Admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions to access this resource."
            )

        # Get server
        server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")

        # Get discovered endpoints
        endpoints = db.query(DiscoveredEndpoint).filter(
            DiscoveredEndpoint.remote_server_id == server_id
        ).all()

        # Transform endpoints into a simple format
        endpoint_data = [
            {
                "id": endpoint.id,
                "path": endpoint.path,
                "method": endpoint.method,
                "status": "active",  # Simplified status
                "last_checked": datetime.now().isoformat(),
                "response_time": 100,  # Example response time
                "status_code": 200,  # Example status code
            }
            for endpoint in endpoints
        ]

        return {
            "server": {
                "id": server.id,
                "name": server.name,
                "base_url": server.base_url,
                "status": server.status
            },
            "endpoints": endpoint_data
        }

    except Exception as e:
        logger.error(f"Error getting test dashboard data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test dashboard data: {str(e)}"
        )

@router.get("/{server_id}/discovered-endpoints", response_model=List[Dict])
@role_required(["Admin"])
def get_discovered_endpoints(
    server_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get discovered endpoints for a specific remote server."""
    server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remote server not found"
        )

    # Get endpoints with their latest health data
    endpoints = db.query(DiscoveredEndpoint).filter(
        DiscoveredEndpoint.remote_server_id == server_id
    ).all()

    endpoint_data = []
    for endpoint in endpoints:
        # Get the latest health record for this endpoint
        latest_health = db.query(EndpointHealth).filter(
            EndpointHealth.discovered_endpoint_id == endpoint.id
        ).order_by(EndpointHealth.checked_at.desc()).first()

        endpoint_data.append({
            "endpoint_id": endpoint.id,
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "parameters": endpoint.parameters,
            "response_schema": endpoint.response_schema,
            "discovered_at": endpoint.discovered_at.isoformat() if endpoint.discovered_at else None,
            "last_checked": endpoint.last_checked.isoformat() if endpoint.last_checked else None,
            "status": endpoint.is_active,
            "health_status": latest_health.is_healthy if latest_health else True,
            "response_time": latest_health.response_time if latest_health else None,
            "status_code": latest_health.status_code if latest_health else None,
            "error_message": latest_health.error_message if latest_health else None,
            "failure_reason": latest_health.failure_reason if latest_health else None,
        })

    return endpoint_data

@router.post("/{server_id}/run-health-scan")
async def run_health_scan(server_id: int, background_tasks: BackgroundTasks):
    """Run health scan for a remote server"""
    try:
        # Initialize the new simple scanner
        scanner = SimpleRemoteScanner()
        
        # Run the scan
        results = await scanner.scan_remote_server(server_id)
        
        # Log results
        healthy_count = sum(1 for r in results if r.get('status', False))
        total_count = len(results)
        logger.info(f"Health scan completed for server {server_id}: {healthy_count}/{total_count} endpoints healthy")
        
        return {
            "status": "success",
            "message": f"Health scan completed: {healthy_count}/{total_count} endpoints healthy",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error running health scan for server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 