from typing import Optional, Dict, List, Any
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
import logging
from urllib.parse import urljoin
import json
from remote_auth_service import RemoteAuthService
from analytics_service import AnalyticsService
from sqlalchemy import text
import httpx
from api_discovery_service import APIDiscoveryService
from endpoint_monitoring_service import EndpointMonitoringService
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemoteServerService:
    def __init__(self, db: Session, user: Optional[Dict] = None):
        self.db = db
        self.user = user
        self.analytics_service = AnalyticsService(db=db, user=user)
        self.auth_service = RemoteAuthService(db)
        self.client = None
        logger.info(f"RemoteServerService initialized with user: {user}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
            self.client = None

    async def get_client(self, server: RemoteServer) -> httpx.AsyncClient:
        """Get an authenticated HTTP client for the remote server."""
        if not self.client:
            self.client = httpx.AsyncClient(
                base_url=server.base_url,
                timeout=30.0
            )
        
        # Get authentication headers
        headers = await self.auth_service.get_auth_headers(server)
        self.client.headers.update(headers)
        
        return self.client

    async def validate_server(self, base_url: str) -> Dict:
        """Validate if the remote server is accessible and has the required endpoints."""
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
                # Try to access the health check endpoint
                response = await client.get("/health")
                if response.status_code == 200:
                    return {"status": "success", "message": "Server is accessible"}
                return {"status": "error", "message": f"Server returned status {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def fetch_endpoints(self, base_url: str, api_key: Optional[str] = None) -> List[Dict]:
        """Fetch available endpoints from the remote server."""
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            async with self.client.get(f"{base_url}/api-management/endpoints", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error fetching endpoints: {e}")
            return []

    async def fetch_analytics(self, base_url: str, api_key: Optional[str] = None) -> Dict:
        """Fetch analytics data from the remote server."""
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            async with self.client.get(f"{base_url}/analytics/summary", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.error(f"Error fetching analytics: {e}")
            return {}

    async def fetch_security_logs(self, base_url: str, api_key: Optional[str] = None) -> List[Dict]:
        """Fetch security logs from the remote server."""
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            async with self.client.get(f"{base_url}/security/logs", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error fetching security logs: {e}")
            return []

    async def update_server_status(self, server: RemoteServer) -> None:
        """Update the status of a remote server."""
        try:
            client = await self.get_client(server)
            response = await client.get("/health")
            server.status = "active" if response.status_code == 200 else "error"
            server.last_checked = datetime.utcnow()
            server.last_error = None
            server.retry_count = 0
        except Exception as e:
            server.status = "error"
            server.last_error = str(e)
            server.retry_count += 1
        finally:
            self.db.commit()

    async def check_all_servers(self) -> None:
        """Check the status of all remote servers."""
        servers = self.db.query(RemoteServer).filter(RemoteServer.is_active == True).all()
        for server in servers:
            await self.update_server_status(server)

    async def get_server_analytics(self, server_id: int, time_range: str = "24h", user: Optional[Dict] = None) -> Dict:
        """Get simplified analytics data for a remote server."""
        try:
            # Get discovered endpoints
            endpoints = self.db.query(DiscoveredEndpoint).filter(
                DiscoveredEndpoint.remote_server_id == server_id
            ).all()

            # Get latest health records for each endpoint
            total_requests = 0
            failed_requests = 0
            client_errors = 0
            server_errors = 0
            total_response_time = 0
            valid_responses = 0

            for endpoint in endpoints:
                latest_health = self.db.query(EndpointHealth).filter(
                    EndpointHealth.discovered_endpoint_id == endpoint.id
                ).order_by(EndpointHealth.checked_at.desc()).first()

                if latest_health:
                    total_requests += 1
                    if not latest_health.is_healthy:
                        failed_requests += 1
                        if latest_health.status_code and 400 <= latest_health.status_code < 500:
                            client_errors += 1
                        elif latest_health.status_code and latest_health.status_code >= 500:
                            server_errors += 1
                    
                    if latest_health.response_time:
                        total_response_time += latest_health.response_time
                        valid_responses += 1

            avg_response_time = total_response_time / valid_responses if valid_responses > 0 else 0

            return {
                "metrics": {
                    "total_requests": total_requests,
                    "failed_requests": failed_requests,
                    "failure_breakdown": {
                        "client_error": client_errors,
                        "server_error": server_errors
                    },
                    "average_response_time": avg_response_time
                }
            }

        except Exception as e:
            logger.error(f"Error getting server analytics: {str(e)}")
            return {
                "metrics": {
                    "total_requests": 0,
                    "failed_requests": 0,
                    "failure_breakdown": {
                        "client_error": 0,
                        "server_error": 0
                    },
                    "average_response_time": 0
                }
            }

    async def get_server_endpoints(self, server_id: int) -> List[Dict]:
        """Get discovered endpoints with their latest health status."""
        try:
            endpoints = self.db.query(DiscoveredEndpoint).filter(
                DiscoveredEndpoint.remote_server_id == server_id
            ).all()

            result = []
            for endpoint in endpoints:
                latest_health = self.db.query(EndpointHealth).filter(
                    EndpointHealth.discovered_endpoint_id == endpoint.id
                ).order_by(EndpointHealth.checked_at.desc()).first()

                endpoint_data = {
                    "id": endpoint.id,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "status": "healthy" if latest_health and latest_health.is_healthy else "unhealthy",
                    "last_checked": latest_health.checked_at if latest_health else None,
                    "response_time": latest_health.response_time if latest_health else None,
                    "status_code": latest_health.status_code if latest_health else None,
                    "failure_reason": latest_health.failure_reason if latest_health else None
                }
                result.append(endpoint_data)

            return result

        except Exception as e:
            logger.error(f"Error getting server endpoints: {str(e)}")
            return []

    async def get_endpoints(self, server_id: int) -> List[Dict]:
        """Get API endpoints from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get("/api-management/endpoints")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching endpoints for server {server_id}: {str(e)}")
            raise

    async def get_threat_logs(self, server_id: int, limit: int = 100) -> List[Dict]:
        """Get threat logs from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get(f"/security/threat-logs?limit={limit}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching threat logs for server {server_id}: {str(e)}")
            raise

    async def get_traffic_logs(self, server_id: int, limit: int = 100) -> List[Dict]:
        """Get traffic logs from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get(f"/analytics/traffic?limit={limit}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching traffic logs for server {server_id}: {str(e)}")
            raise

    async def get_vulnerability_scans(self, server_id: int) -> List[Dict]:
        """Get vulnerability scan results from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get("/security/vulnerability-scans")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching vulnerability scans for server {server_id}: {str(e)}")
            raise

    async def get_activity_logs(self, server_id: int, limit: int = 100) -> List[Dict]:
        """Get activity logs from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get(f"/security/activity-logs?limit={limit}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching activity logs for server {server_id}: {str(e)}")
            raise

    async def get_rate_limits(self, server_id: int) -> List[Dict]:
        """Get rate limit information from a remote server."""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        try:
            client = await self.get_client(server)
            response = await client.get("/security/rate-limits")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching rate limits for server {server_id}: {str(e)}")
            raise

    async def discover_and_monitor(self, server_id: int) -> Dict[str, Any]:
        """Discover and start monitoring endpoints for a remote server"""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            return {"status": "error", "message": "Server not found"}
            
        try:
            # Initialize services
            discovery = APIDiscoveryService(self.db, server)
            monitor = EndpointMonitoringService(self.db, server)
            
            # Discover endpoints
            endpoints = await discovery.discover_endpoints()
            
            # Store discovered endpoints
            await discovery.store_discovered_endpoints(endpoints)
            
            # Start monitoring
            monitoring_results = []
            for endpoint in server.discovered_endpoints:
                if endpoint.is_active:
                    result = await monitor.monitor_endpoint(endpoint)
                    monitoring_results.append({
                        "endpoint": endpoint.path,
                        "method": endpoint.method,
                        "result": result
                    })
            
            return {
                "status": "success",
                "endpoints_discovered": len(endpoints),
                "endpoints_monitored": len(monitoring_results),
                "monitoring_results": monitoring_results
            }
            
        except Exception as e:
            logger.error(f"Error in discover_and_monitor for server {server_id}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def get_server_metrics(self, server_id: int) -> Dict[str, Any]:
        """Get aggregated metrics for a server"""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            return {}
            
        # Get all health records for the server's endpoints
        endpoint_ids = [e.id for e in server.discovered_endpoints]
        health_records = self.db.query(EndpointHealth)\
            .filter(EndpointHealth.discovered_endpoint_id.in_(endpoint_ids))\
            .all()
            
        # Calculate metrics
        total_requests = len(health_records)
        successful_requests = sum(1 for r in health_records if r.is_healthy)
        failed_requests = total_requests - successful_requests
        
        avg_response_time = sum(r.response_time for r in health_records if r.response_time) / len(health_records) if health_records else 0
        
        # Count failures by reason
        failure_counts = {}
        for record in health_records:
            if not record.is_healthy and record.failure_reason:
                failure_counts[record.failure_reason] = failure_counts.get(record.failure_reason, 0) + 1
                
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "average_response_time": avg_response_time,
            "failure_breakdown": failure_counts
        }

class RemoteAPIClient:
    def __init__(self, server: RemoteServer, auth_service: RemoteAuthService):
        self.server = server
        self.auth_service = auth_service
        self.session = None
        self._base_url = server.base_url.rstrip('/')
        self._endpoints_cache = None

    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on server configuration."""
        headers = {}
        
        if self.server.auth_type == "basic":
            # Basic auth
            if self.server.username and self.server.password:
                auth = aiohttp.BasicAuth(self.server.username, self.server.password)
                headers["Authorization"] = auth.encode()
        elif self.server.auth_type == "token":
            # Token-based auth
            if self.server.access_token:
                headers["Authorization"] = f"Bearer {self.server.access_token}"
            elif self.server.token_endpoint:
                # Get new token
                token = await self.auth_service.authenticate(self.server)
                if token:
                    headers["Authorization"] = f"Bearer {token}"
        
        if self.server.api_key:
            headers["X-API-Key"] = self.server.api_key
            
        return headers

    async def discover_endpoints(self) -> List[Dict]:
        """Discover available endpoints from the FastAPI server."""
        try:
            # Try OpenAPI JSON first
            headers = await self._get_auth_headers()
            async with self.session.get(f"{self._base_url}/openapi.json", headers=headers) as response:
                if response.status == 200:
                    openapi_data = await response.json()
                    return self._parse_openapi_spec(openapi_data)
                
            # Fallback to /docs
            async with self.session.get(f"{self._base_url}/docs", headers=headers) as response:
                if response.status == 200:
                    # Parse the HTML to extract endpoints
                    html = await response.text()
                    return self._parse_docs_html(html)
                
            return []
            
        except Exception as e:
            logger.error(f"Error discovering endpoints: {str(e)}")
            return []

    def _parse_openapi_spec(self, openapi_data: Dict) -> List[Dict]:
        """Parse OpenAPI specification to extract endpoints."""
        endpoints = []
        
        for path, path_item in openapi_data.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "description": operation.get("description", ""),
                        "tags": operation.get("tags", []),
                        "parameters": operation.get("parameters", []),
                        "responses": operation.get("responses", {})
                    }
                    endpoints.append(endpoint)
        
        return endpoints

    def _parse_docs_html(self, html: str) -> List[Dict]:
        """Parse FastAPI docs HTML to extract endpoints."""
        # This is a simplified version. In practice, you'd want to use proper HTML parsing
        endpoints = []
        # Add HTML parsing logic here
        return endpoints

    async def get_health_status(self) -> Dict:
        """Get health status from the remote server."""
        try:
            headers = await self._get_auth_headers()
            async with self.session.get(f"{self._base_url}/health", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return {"status": "error", "message": f"Health check failed with status {response.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_analytics(self) -> Dict:
        """Get analytics data from the remote server."""
        try:
            headers = await self._get_auth_headers()
            async with self.session.get(f"{self._base_url}/analytics/summary", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {}

    async def get_security_logs(self) -> List[Dict]:
        """Get security logs from the remote server."""
        try:
            headers = await self._get_auth_headers()
            async with self.session.get(f"{self._base_url}/security/logs", headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting security logs: {str(e)}")
            return []

    async def get_endpoint_metrics(self, path: str) -> Dict:
        """Get metrics for a specific endpoint."""
        try:
            headers = await self._get_auth_headers()
            async with self.session.get(
                f"{self._base_url}/analytics/endpoints/{path}",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}
        except Exception as e:
            logger.error(f"Error getting endpoint metrics: {str(e)}")
            return {}

    async def monitor_endpoint(self, path: str, method: str = "GET") -> Dict:
        """Monitor a specific endpoint's performance."""
        try:
            headers = await self._get_auth_headers()
            start_time = datetime.now(timezone.utc)
            
            async with self.session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers
            ) as response:
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                return {
                    "status": response.status,
                    "response_time": response_time,
                    "headers": dict(response.headers),
                    "timestamp": start_time.isoformat()
                }
        except Exception as e:
            logger.error(f"Error monitoring endpoint {path}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

class AnalyticsService:
    def __init__(self, db: Session, user: Optional[Dict] = None):
        self.db = db
        self.user = user
        logger.info(f"AnalyticsService initialized with user: {user}")

    async def get_server_analytics(self, server_id: int, time_range: str = "24h", user: Optional[Dict] = None) -> Dict:
        """Get analytics data for a server."""
        # Fallback to instance user if not provided
        user = user or self.user
        logger.info(f"AnalyticsService.get_server_analytics called with:")
        logger.info(f"  server_id={server_id}")
        logger.info(f"  time_range={time_range}")
        logger.info(f"  user={user}")
        logger.info(f"  instance user={self.user}")
        
        # Get the server
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            raise ValueError("Server not found")

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        if time_range == "24h":
            start_time = end_time - timedelta(hours=24)
        elif time_range == "7d":
            start_time = end_time - timedelta(days=7)
        elif time_range == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)  # Default to 24h

        # Get analytics data
        try:
            logger.info("Getting server metrics...")
            metrics = await self.get_server_metrics(server_id)
            
            logger.info("Getting server endpoints...")
            endpoints = await self.get_server_endpoints(server_id)
            
            logger.info("Getting response time data...")
            response_times = await self.get_response_time_data(server_id, start_time, end_time)
            
            logger.info("Analytics data retrieved successfully")
            return {
                "metrics": metrics,
                "endpoints": endpoints,
                "response_times": response_times,
                "time_range": time_range,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting server analytics: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            raise

    async def get_server_metrics(self, server_id: int) -> Dict[str, Any]:
        """Get aggregated metrics for a server"""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            return {}
            
        # Get all health records for the server's endpoints
        endpoint_ids = [e.id for e in server.discovered_endpoints]
        health_records = self.db.query(EndpointHealth)\
            .filter(EndpointHealth.discovered_endpoint_id.in_(endpoint_ids))\
            .all()
            
        # Calculate metrics
        total_requests = len(health_records)
        successful_requests = sum(1 for r in health_records if r.is_healthy)
        failed_requests = total_requests - successful_requests
        
        avg_response_time = sum(r.response_time for r in health_records if r.response_time) / len(health_records) if health_records else 0
        
        # Count failures by reason
        failure_counts = {}
        for record in health_records:
            if not record.is_healthy and record.failure_reason:
                failure_counts[record.failure_reason] = failure_counts.get(record.failure_reason, 0) + 1
                
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "average_response_time": avg_response_time,
            "failure_breakdown": failure_counts
        }

    async def get_server_endpoints(self, server_id: int) -> List[Dict[str, Any]]:
        """Get all endpoints for a server with their latest health status"""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            return []
            
        endpoints = []
        for endpoint in server.discovered_endpoints:
            # Get latest health record
            latest_health = self.db.query(EndpointHealth)\
                .filter(EndpointHealth.discovered_endpoint_id == endpoint.id)\
                .order_by(EndpointHealth.checked_at.desc())\
                .first()
                
            endpoint_data = {
                "id": endpoint.id,
                "path": endpoint.path,
                "method": endpoint.method,
                "description": endpoint.description,
                "is_active": endpoint.is_active,
                "discovered_at": endpoint.discovered_at,
                "last_checked": endpoint.last_checked,
                "health_status": latest_health.status if latest_health else None,
                "response_time": latest_health.response_time if latest_health else None,
                "status_code": latest_health.status_code if latest_health else None,
                "error_message": latest_health.error_message if latest_health else None,
                "failure_reason": latest_health.failure_reason if latest_health else None
            }
            endpoints.append(endpoint_data)
            
        return endpoints

    async def get_response_time_data(self, server_id: int, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get response time data for a server within a time range"""
        server = self.db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not server:
            return []
            
        # Get all health records for the server's endpoints within the time range
        endpoint_ids = [e.id for e in server.discovered_endpoints]
        health_records = self.db.query(EndpointHealth)\
            .filter(
                EndpointHealth.discovered_endpoint_id.in_(endpoint_ids),
                EndpointHealth.checked_at >= start_time,
                EndpointHealth.checked_at <= end_time
            )\
            .order_by(EndpointHealth.checked_at)\
            .all()
            
        # Format the data
        response_times = []
        for record in health_records:
            response_times.append({
                "timestamp": record.checked_at.isoformat(),
                "endpoint_id": record.discovered_endpoint_id,
                "response_time": record.response_time,
                "status_code": record.status_code,
                "is_healthy": record.is_healthy
            })
            
        return response_times 