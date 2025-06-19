import httpx
import logging
from typing import List, Dict, Any
from models import RemoteServer, DiscoveredEndpoint
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)

class APIDiscoveryService:
    def __init__(self, db: Session, server: RemoteServer):
        self.db = db
        self.server = server
        self.client = httpx.AsyncClient(timeout=30.0)
        
    def _generate_endpoint_hash(self, path: str, method: str, parameters: list) -> str:
        """Generate a unique hash for an endpoint based on its path, method, and parameters"""
        # Sort parameters to ensure consistent hashing
        sorted_params = sorted(parameters, key=lambda x: x.get('name', ''))
        data = f"{path}:{method}:{json.dumps(sorted_params)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def discover_endpoints(self):
        """Discover endpoints from the remote server's OpenAPI documentation"""
        try:
            # Try different possible OpenAPI documentation URLs
            openapi_urls = [
                f"{self.server.base_url}/openapi.json",
                f"{self.server.base_url}/docs/openapi.json",
                f"{self.server.base_url}/swagger.json",
                f"{self.server.base_url}/api-docs"
            ]
            
            openapi_doc = None
            for url in openapi_urls:
                try:
                    response = await self.client.get(url)
                    if response.status_code == 200:
                        openapi_doc = response.json()
                        logger.info(f"Found OpenAPI documentation at {url}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to fetch OpenAPI doc from {url}: {str(e)}")
                    continue
            
            if not openapi_doc:
                logger.error(f"Could not find OpenAPI documentation for server {self.server.name}")
                return []
            
            # Track unique endpoints using their hashes
            unique_endpoints = {}
            
            for path, path_item in openapi_doc.get("paths", {}).items():
                for method, operation in path_item.items():
                    if method.lower() in ["get", "post", "put", "delete", "patch"]:
                        parameters = operation.get("parameters", [])
                        endpoint_hash = self._generate_endpoint_hash(path, method, parameters)
                        
                        if endpoint_hash not in unique_endpoints:
                            unique_endpoints[endpoint_hash] = {
                                "path": path,
                                "method": method.upper(),
                                "description": operation.get("description", ""),
                                "parameters": parameters,
                                "response_schema": operation.get("responses", {}).get("200", {}).get("content", {}),
                                "hash": endpoint_hash
                            }
            
            logger.info(f"Discovered {len(unique_endpoints)} unique endpoints from {self.server.name}")
            return list(unique_endpoints.values())
            
        except Exception as e:
            logger.error(f"Failed to discover endpoints for server {self.server.name}: {str(e)}")
            return []
        finally:
            await self.client.aclose()
    
    async def store_discovered_endpoints(self, endpoints):
        """Store discovered endpoints in the database with deduplication"""
        try:
            # Get existing endpoints for this server
            existing_endpoints = {
                endpoint.endpoint_hash: endpoint 
                for endpoint in self.db.query(DiscoveredEndpoint).filter(
                    DiscoveredEndpoint.remote_server_id == self.server.id
                ).all()
            }
            
            for endpoint_data in endpoints:
                endpoint_hash = endpoint_data["hash"]
                
                if endpoint_hash in existing_endpoints:
                    # Update existing endpoint
                    existing = existing_endpoints[endpoint_hash]
                    existing.description = endpoint_data["description"]
                    existing.parameters = endpoint_data["parameters"]
                    existing.response_schema = endpoint_data["response_schema"]
                    existing.last_checked = datetime.utcnow()
                    existing.is_active = True
                else:
                    # Create new endpoint
                    new_endpoint = DiscoveredEndpoint(
                        remote_server_id=self.server.id,
                        path=endpoint_data["path"],
                        method=endpoint_data["method"],
                        description=endpoint_data["description"],
                        parameters=endpoint_data["parameters"],
                        response_schema=endpoint_data["response_schema"],
                        discovered_at=datetime.utcnow(),
                        last_checked=datetime.utcnow(),
                        is_active=True,
                        endpoint_hash=endpoint_hash
                    )
                    self.db.add(new_endpoint)
            
            # Mark endpoints not found in discovery as inactive
            current_hashes = {endpoint["hash"] for endpoint in endpoints}
            for hash_value, endpoint in existing_endpoints.items():
                if hash_value not in current_hashes:
                    endpoint.is_active = False
            
            self.db.commit()
            logger.info(f"Stored {len(endpoints)} endpoints for server {self.server.name}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to store endpoints for server {self.server.name}: {str(e)}")
            raise 