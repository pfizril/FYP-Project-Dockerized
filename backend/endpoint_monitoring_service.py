import httpx
import logging
import time
import base64
from sqlalchemy.orm import Session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
from datetime import datetime
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class EndpointMonitoringService:
    def __init__(self, db: Session, server: RemoteServer):
        self.db = db
        self.server = server
        self.session = None
    
    async def _get_auth_headers(self):
        """Get authentication headers based on server configuration"""
        headers = {}
        
        if self.server.auth_type == "basic" and self.server.username and self.server.password:
            # Basic auth
            auth_str = f"{self.server.username}:{self.server.password}"
            auth_bytes = auth_str.encode('ascii')
            base64_bytes = base64.b64encode(auth_bytes)
            headers['Authorization'] = f"Basic {base64_bytes.decode('ascii')}"
            
        elif self.server.auth_type == "token" and self.server.access_token:
            # Token auth
            headers['Authorization'] = f"Bearer {self.server.access_token}"
            
        elif self.server.auth_type == "api_key" and self.server.api_key:
            # API key auth
            headers['X-API-Key'] = self.server.api_key
            
        return headers
    
    async def monitor_endpoint(self, endpoint: DiscoveredEndpoint) -> dict:
        """Monitor a single endpoint"""
        try:
            # Get authentication headers
            headers = await self._get_auth_headers()
            
            # Make request to endpoint
            url = f"{self.server.base_url.rstrip('/')}/{endpoint.path.lstrip('/')}"
            logger.info(f"Monitoring endpoint: {url}")
            
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=endpoint.method,
                    url=url,
                    headers=headers,
                    timeout=30
                ) as response:
                    response_time = time.time() - start_time
                    
                    # Record health status
                    health = EndpointHealth(
                        discovered_endpoint_id=endpoint.id,
                        status_code=response.status,
                        response_time=response_time,
                        is_healthy=200 <= response.status < 300,
                        status="success" if 200 <= response.status < 300 else "error",
                        failure_reason=None if 200 <= response.status < 300 else self._categorize_failure(response.status),
                        checked_at=datetime.utcnow()
                    )
                    self.db.add(health)
                    self.db.commit()  # Ensure health record is saved
                    
                    return {
                        "status": "success" if 200 <= response.status < 300 else "error",
                        "status_code": response.status,
                        "response_time": response_time
                    }
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout monitoring endpoint {endpoint.path}")
            health = EndpointHealth(
                discovered_endpoint_id=endpoint.id,
                status_code=None,
                response_time=None,
                is_healthy=False,
                status="error",
                failure_reason="timeout",
                checked_at=datetime.utcnow()
            )
            self.db.add(health)
            self.db.commit()  # Ensure health record is saved
            return {"status": "error", "error": "timeout"}
            
        except Exception as e:
            logger.error(f"Error monitoring endpoint {endpoint.path}: {str(e)}")
            health = EndpointHealth(
                discovered_endpoint_id=endpoint.id,
                status_code=None,
                response_time=None,
                is_healthy=False,
                status="error",
                failure_reason="request_error",
                checked_at=datetime.utcnow()
            )
            self.db.add(health)
            self.db.commit()  # Ensure health record is saved
            return {"status": "error", "error": "request_error"}
    
    async def close(self):
        """Close any open connections"""
        if self.session:
            await self.session.close()
    
    def _categorize_failure(self, status_code: int) -> str:
        """Categorize HTTP status code into failure reason"""
        if status_code >= 500:
            return "server_error"
        elif status_code == 401:
            return "authentication_required"
        elif status_code == 403:
            return "authorization_required"
        elif status_code == 404:
            return "endpoint_not_found"
        elif status_code == 422:
            return "validation_error"
        elif status_code >= 400:
            return "client_error"
        else:
            return "unknown_error" 