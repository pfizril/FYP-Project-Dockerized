from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials, OAuth2PasswordBearer
from datetime import datetime, timedelta
import random
import secrets
from typing import List, Dict
import logging
import json
import time
import base64
import os
from dotenv import load_dotenv
from jose import jwt
from decimal import Decimal

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
security = HTTPBasic()

# Get secret key from environment or use default for testing
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Mock data storage
mock_data = {
    "analytics": [],
    "endpoints": [],
    "threat_logs": [],
    "traffic_logs": [],
    "vulnerability_scans": [],
    "activity_logs": [],
    "rate_limits": []
}

def generate_mock_data():
    """Generate mock data for testing."""
    # Generate mock analytics
    mock_data["analytics"] = {
        "total_requests": random.randint(1000, 5000),
        "average_response_time": random.uniform(0.1, 2.0),
        "error_rate": random.uniform(0.01, 0.05),
        "requests_by_endpoint": {
            "/api/v1/users": random.randint(100, 500),
            "/api/v1/products": random.randint(200, 800),
            "/api/v1/orders": random.randint(50, 300)
        }
    }
    
    # Generate mock endpoints
    mock_data["endpoints"] = [
        {
            "path": "/api/v1/users",
            "method": "GET",
            "description": "Get user list",
            "rate_limit": "100/minute"
        },
        {
            "path": "/api/v1/products",
            "method": "GET",
            "description": "Get product list",
            "rate_limit": "200/minute"
        }
    ]
    
    # Generate mock threat logs
    mock_data["threat_logs"] = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "brute_force",
            "ip": f"192.168.1.{random.randint(1, 255)}",
            "status": "blocked"
        }
        for _ in range(5)
    ]
    
    # Generate mock traffic logs
    mock_data["traffic_logs"] = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": "/api/v1/users",
            "method": "GET",
            "status_code": 200,
            "response_time": random.uniform(0.1, 1.0)
        }
        for _ in range(10)
    ]
    
    # Generate mock vulnerability scans
    mock_data["vulnerability_scans"] = [
        {
            "scan_id": f"scan_{i}",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": random.choice(["low", "medium", "high"]),
            "description": f"Test vulnerability {i}"
        }
        for i in range(3)
    ]
    
    # Generate mock activity logs
    mock_data["activity_logs"] = [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "user": f"user_{i}",
            "action": random.choice(["login", "logout", "create", "update", "delete"]),
            "resource": f"/api/v1/{random.choice(['users', 'products', 'orders'])}"
        }
        for i in range(8)
    ]
    
    # Generate mock rate limits
    mock_data["rate_limits"] = [
        {
            "endpoint": "/api/v1/users",
            "limit": "100/minute",
            "remaining": random.randint(0, 100),
            "reset": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
        },
        {
            "endpoint": "/api/v1/products",
            "limit": "200/minute",
            "remaining": random.randint(0, 200),
            "reset": (datetime.utcnow() + timedelta(minutes=1)).isoformat()
        }
    ]

# Generate initial mock data
generate_mock_data()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = "fizril2001"
    correct_password = "fizril2001"
    is_correct_username = secrets.compare_digest(credentials.username, correct_username)
    is_correct_password = secrets.compare_digest(credentials.password, correct_password)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

async def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is missing"
        )
    # Get API key from environment or use default
    correct_api_key = os.getenv("API_KEY", "test-api-key")
    if not secrets.compare_digest(x_api_key, correct_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return x_api_key

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials"
            )
        return {"username": username, "id": user_id, "role": user_role}
    except jwt.JWTError:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/analytics/summary")
async def get_analytics_summary(
    time_range: str = "24h",
    api_key: str = Depends(verify_api_key),
    current_user: dict = Depends(get_current_user)
):
    """Get analytics summary."""
    logger.info(f"Received analytics summary request with time_range: {time_range}")
    logger.info(f"Request from user: {current_user['username']}")
    try:
        # For test server, return mock data
        mock_data = {
            "summary": {
                "total_requests": 1000,
                "success_rate": Decimal('98.5'),
                "average_response_time": Decimal('150.0'),
                "error_rate": Decimal('1.5'),
                "active_endpoints": 15,
                "total_endpoints": 20,
                "average_uptime": Decimal('99.9'),
                "average_error_rate": Decimal('0.1'),
                "health_check_response_time": Decimal('120.0')
            },
            "time_range": time_range,
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert Decimal values to float for JSON serialization
        for key, value in mock_data["summary"].items():
            if isinstance(value, Decimal):
                mock_data["summary"][key] = float(value)
        
        return mock_data
    except Exception as e:
        logger.error(f"Error in analytics summary endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating analytics summary: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint to verify server is running."""
    return {
        "status": "running",
        "endpoints": [
            "/health",
            "/analytics/summary",
            "/api-management/endpoints",
            "/security/threat-logs",
            "/analytics/traffic",
            "/security/vulnerability-scans",
            "/security/activity-logs",
            "/security/rate-limits"
        ]
    }

@app.get("/api-management/endpoints")
async def get_endpoints(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    """Get API endpoints."""
    logger.info("Received endpoints request")
    return mock_data["endpoints"]

@app.get("/security/threat-logs")
async def get_threat_logs(
    limit: int = 100,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
):
    """Get threat logs."""
    logger.info(f"Received threat logs request with limit: {limit}")
    return mock_data["threat_logs"][:limit]

@app.get("/analytics/traffic")
async def get_traffic_logs(
    limit: int = 100,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
):
    """Get traffic logs."""
    logger.info(f"Received traffic logs request with limit: {limit}")
    return mock_data["traffic_logs"][:limit]

@app.get("/security/vulnerability-scans")
async def get_vulnerability_scans(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    """Get vulnerability scan results."""
    logger.info("Received vulnerability scans request")
    return mock_data["vulnerability_scans"]

@app.get("/security/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    credentials: HTTPBasicCredentials = Depends(verify_credentials)
):
    """Get activity logs."""
    logger.info(f"Received activity logs request with limit: {limit}")
    return mock_data["activity_logs"][:limit]

@app.get("/security/rate-limits")
async def get_rate_limits(credentials: HTTPBasicCredentials = Depends(verify_credentials)):
    """Get rate limit information."""
    logger.info("Received rate limits request")
    return mock_data["rate_limits"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 