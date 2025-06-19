#!/usr/bin/env python
"""
Simple and reliable remote server scanner
"""
import asyncio
import logging
import time
from datetime import datetime
import aiohttp
from database import get_db_session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("simple_scanner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simple_scanner")

class SimpleRemoteScanner:
    def __init__(self):
        self.session = None
        self.base_url = None
        self.basic_auth = None
    
    async def initialize(self, base_url: str, basic_auth: tuple = None):
        """Initialize scanner with basic settings"""
        self.base_url = base_url.rstrip('/')
        self.basic_auth = basic_auth
        
        # Create a simple session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        logger.info(f"Initialized scanner with base URL: {self.base_url}")
    
    async def close(self):
        """Close the scanner"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_headers(self):
        """Get basic headers"""
        headers = {
            "Accept": "application/json"
        }
        
        # Add Basic Auth if configured
        if self.basic_auth:
            import base64
            auth_str = f"{self.basic_auth[0]}:{self.basic_auth[1]}"
            auth_bytes = auth_str.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            headers["Authorization"] = f"Basic {base64_auth}"
        
        return headers
    
    async def check_endpoint(self, endpoint: DiscoveredEndpoint) -> dict:
        """Check a single endpoint"""
        start_time = time.time()
        
        try:
            # Construct URL
            url = endpoint.path if endpoint.path.startswith(('http://', 'https://')) else f"{self.base_url}/{endpoint.path.lstrip('/')}"
            
            # Handle path parameters
            if '{' in url:
                url = url.replace('{matric_no}', 'A123456')
                url = url.replace('{id}', '1')
            
            logger.info(f"Checking endpoint: {url}")
            
            # Make request
            async with self.session.request(
                method=endpoint.method,
                url=url,
                headers=self._get_headers(),
                json=None if endpoint.method == 'GET' else {}  # Only add empty JSON for non-GET requests
            ) as response:
                response_time = time.time() - start_time
                
                # Get response body for debugging
                try:
                    response_body = await response.text()
                    logger.debug(f"Response: {response_body[:200]}...")
                except:
                    pass
                
                # Check if response is successful
                is_success = 200 <= response.status < 400
                
                result = {
                    "status": is_success,
                    "url": url,
                    "status_code": response.status,
                    "response_time": response_time,
                    "is_disabled": False,
                    "is_error": not is_success,
                    "failure_reason": self._get_failure_reason(response.status),
                    "error_message": f"HTTP {response.status}"
                }
                
                logger.info(f"Result for {url}: status={is_success}, code={response.status}, time={response_time:.3f}s")
                return result
                
        except Exception as e:
            logger.error(f"Error checking {endpoint.path}: {str(e)}")
            return {
                "status": False,
                "url": endpoint.path,
                "error": str(e),
                "is_disabled": False,
                "is_error": True,
                "failure_reason": "connection_error",
                "error_message": str(e)
            }
    
    def _get_failure_reason(self, status_code: int) -> str:
        """Get failure reason from status code"""
        if status_code == 401:
            return "authentication_required"
        elif status_code == 403:
            return "forbidden"
        elif status_code == 404:
            return "not_found"
        elif status_code == 405:
            return "method_not_allowed"
        elif status_code == 422:
            return "validation_error"
        elif status_code == 429:
            return "rate_limited"
        elif 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown_error"
    
    async def scan_remote_server(self, server_id: int, batch_size: int = 5) -> List[Dict[str, Any]]:
        """Scan all endpoints for a remote server"""
        try:
            # Get server details
            with get_db_session() as db:
                server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
                if not server:
                    raise ValueError(f"Server {server_id} not found")
                
                # Get active endpoints
                endpoints = db.query(DiscoveredEndpoint).filter(
                    DiscoveredEndpoint.remote_server_id == server_id,
                    DiscoveredEndpoint.is_active == True
                ).all()
                
                logger.info(f"Found {len(endpoints)} active endpoints for server {server_id}")
            
            # Initialize scanner
            await self.initialize(
                base_url=server.base_url,
                basic_auth=(server.username, server.password) if server.auth_type == "basic" else None
            )
            
            # Check each endpoint
            results = []
            for endpoint in endpoints:
                result = await self.check_endpoint(endpoint)
                results.append(result)
                
                # Save result to database
                with get_db_session() as db:
                    try:
                        health_record = EndpointHealth(
                            discovered_endpoint_id=endpoint.id,
                            status=result["status"],
                            is_healthy=result["status"],
                            response_time=result["response_time"],
                            checked_at=datetime.now(),
                            status_code=result.get("status_code"),
                            error_message=result.get("error_message"),
                            failure_reason=result.get("failure_reason")
                        )
                        db.add(health_record)
                        db.commit()
                        logger.info(f"Saved health check result for endpoint {endpoint.path}")
                    except Exception as e:
                        logger.error(f"Error saving health check result: {e}")
                        db.rollback()
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning server {server_id}: {e}")
            raise
        finally:
            await self.close()

async def main():
    """Main function to run the scanner"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python simple_remote_scanner.py <server_id>")
        sys.exit(1)
    
    try:
        server_id = int(sys.argv[1])
        scanner = SimpleRemoteScanner()
        results = await scanner.scan_remote_server(server_id)
        
        # Print summary
        total = len(results)
        successful = sum(1 for r in results if r["status"])
        print(f"\nScan complete:")
        print(f"Total endpoints: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success rate: {(successful/total*100):.1f}%")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 