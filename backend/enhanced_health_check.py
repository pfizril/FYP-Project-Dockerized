import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import FormData, ClientTimeout, TCPConnector
from database import session
from models import APIEndpoint, EndpointHealth, DiscoveredEndpoint, APIRequest
from endpoint_config import endpoint_config_manager, EndpointConfig, HTTPMethod
import os
from create_test_data import create_test_data
from database import get_db_session

logger = logging.getLogger("enhanced_health_check")

class HealthChecker:
    def __init__(self):
        self._is_initialized = False
        self._test_data = None
        self._headers = None

    async def initialize(self):
        """Initialize the health checker with fresh test data"""
        try:
            # Create fresh test data
            self._test_data = create_test_data()
            
            # Update headers with new API key
            self._headers = {
                "X-API-Key": self._test_data['api_key'],
                "Content-Type": "application/json"
            }
            
            # Update endpoint configuration with new IDs
            self._update_endpoint_config()
            
            self._is_initialized = True
            logger.info("Health checker initialized with fresh test data")
        except Exception as e:
            logger.error(f"Failed to initialize health checker: {e}")
            raise

    def _update_endpoint_config(self):
        """Update endpoint configuration with new test data IDs"""
        if not self._test_data:
            return

        # Update user-related endpoints
        config = endpoint_config_manager.get_config("/auth/api-keys/generate/{user_id}")
        if config:
            config.url = f"/auth/api-keys/generate/{self._test_data['user_id']}"
        
        config = endpoint_config_manager.get_config("/auth/api-keys/{user_id}")
        if config:
            config.url = f"/auth/api-keys/{self._test_data['user_id']}"
        
        config = endpoint_config_manager.get_config("/auth/users/update-role/{user_id}")
        if config:
            config.url = f"/auth/users/update-role/{self._test_data['user_id']}?new_role=Admin"
        
        # Update API key endpoints
        config = endpoint_config_manager.get_config("/auth/api-keys/revoke/{key_id}")
        if config:
            config.url = f"/auth/api-keys/revoke/{self._test_data['key_id']}"
        
        # Update endpoint management endpoints
        config = endpoint_config_manager.get_config("/api-management/endpoints-update/{endpoint_id}")
        if config:
            config.url = f"/api-management/endpoints-update/{self._test_data['endpoint_id']}"
        
        config = endpoint_config_manager.get_config("/api-management/delete-endpoints/{endpoint_id}")
        if config:
            config.url = f"/api-management/delete-endpoints/{self._test_data['endpoint_id']}"
        
        config = endpoint_config_manager.get_config("/api-management/endpoints/toggle_status/{endpoint_id}")
        if config:
            config.url = f"/api-management/endpoints/toggle_status/{self._test_data['endpoint_id']}?status=true"
        
        # Update test endpoint
        config = endpoint_config_manager.get_config("/test/health-check")
        if config:
            config.url = self._test_data['endpoint_url']
        
        logger.info("Updated endpoint configuration with new test data IDs")

class EnhancedHealthChecker:
    """Enhanced health checker for API endpoints"""
    
    def __init__(self):
        self.session = None
        self.base_url = None
        self.auth_token = None
        self._is_initialized = False
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self._loop = None  # Store the event loop
        self.basic_auth = None  # Store Basic Auth credentials
    
    async def initialize(self, base_url: str = None, basic_auth: tuple = None):
        """Initialize the health checker and get authentication token"""
        if self._is_initialized:
            logger.warning("Health checker already initialized")
            return

        try:
            # Store the current event loop
            self._loop = asyncio.get_running_loop()
            
            # Close any existing session before creating a new one
            if self.session and not self.session.closed:
                await self.session.close()
            
            # Create session with custom timeout and connection settings
            timeout = ClientTimeout(total=30)  # 30 seconds total timeout
            connector = TCPConnector(
                force_close=True,  # Force close connections
                enable_cleanup_closed=True,  # Clean up closed connections
                limit=10  # Limit concurrent connections
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                loop=self._loop  # Explicitly set the loop
            )
            
            # Set base URL and auth if provided
            if base_url:
                self.base_url = base_url.rstrip('/')  # Remove trailing slash
            else:
                self.base_url = "http://localhost:8000"
            
            if basic_auth:
                self.basic_auth = basic_auth
            
            logger.info(f"Using base URL: {self.base_url}")
            
            # Get authentication token if not using Basic Auth
            if not self.basic_auth:
                for attempt in range(self.max_retries):
                    try:
                        # Get fresh test data for authentication
                        from create_test_data import create_test_data
                        test_data = create_test_data()
                        
                        # Create form data matching OAuth2PasswordRequestForm format
                        form_data = FormData()
                        form_data.add_field('grant_type', 'password')
                        form_data.add_field('username', 'health_check_user')
                        form_data.add_field('password', 'test_password')
                        
                        # Use the API key from test data
                        headers = {
                            "X-API-KEY": test_data['api_key'],
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                        
                        async with self.session.post(
                            f"{self.base_url}/auth/token",
                            data=form_data,
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                self.auth_token = data.get("access_token")
                                logger.info("Successfully obtained authentication token")
                                self._is_initialized = True
                                return
                            else:
                                logger.error(f"Failed to get authentication token: {response.status}")
                                try:
                                    error_data = await response.json()
                                    logger.error(f"Auth error details: {error_data}")
                                except:
                                    logger.error("Could not get error details from response")
                                
                                if attempt < self.max_retries - 1:
                                    logger.info(f"Retrying authentication in {self.retry_delay} seconds...")
                                    await asyncio.sleep(self.retry_delay)
                                    continue
                                
                                await self.close()
                    except Exception as e:
                        logger.error(f"Error during authentication: {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        await self.close()
            else:
                self._is_initialized = True
                
        except Exception as e:
            logger.error(f"Error initializing health checker: {e}")
            await self.close()
    
    async def close(self):
        """Close the health checker and cleanup resources"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                logger.info("Successfully closed aiohttp session")
            except Exception as e:
                logger.error(f"Error closing aiohttp session: {e}")
        self.session = None
        self.auth_token = None
        self._is_initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def _get_full_url(self, url: str) -> str:
        """Get the full URL for the request"""
        if url.startswith(('http://', 'https://')):
            return url
        # Remove any leading slashes to avoid double slashes
        url = url.lstrip('/')
        # If base_url is set, use it, otherwise default to localhost
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{url}"
        return f"http://localhost:8000/{url}"
    
    def _prepare_headers(self, config: EndpointConfig) -> Dict[str, str]:
        """Prepare headers for the request"""
        headers = {
            "X-Health-Check": "true"
        }
        
        # Get fresh test data for API key
        try:
            from create_test_data import create_test_data
            test_data = create_test_data()
            headers["X-API-KEY"] = test_data['api_key']
        except Exception as e:
            logger.error(f"Failed to get API key from test data: {e}")
            # Fallback to a default API key if needed
            headers["X-API-KEY"] = "health-monitor-key-35c4d4b753db1940"
        
        # Add Basic Auth if configured
        if self.basic_auth:
            import base64
            auth_str = f"{self.basic_auth[0]}:{self.basic_auth[1]}"
            auth_bytes = auth_str.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            headers["Authorization"] = f"Basic {base64_auth}"
        # Add Bearer token if available
        elif self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        # Only add Content-Type for POST/PUT/PATCH requests
        if config and config.method in ['POST', 'PUT', 'PATCH']:
            headers["Content-Type"] = "application/json"
            
        return headers
    
    async def check_endpoint(self, config: EndpointConfig) -> Dict[str, Any]:
        """Check a single endpoint"""
        if not self._is_initialized:
            logger.error("Health checker not initialized")
            return {"status": False, "error": "Health checker not initialized"}
            
        if not self.session or self.session.closed:
            logger.error("Session is closed or not initialized")
            return {"status": False, "error": "Session is closed or not initialized"}
            
        start_time = time.time()
        try:
            headers = self._prepare_headers(config)
            url = self._get_full_url(config.url)
            
            # First check if endpoint exists and is enabled
            with get_db_session() as db:
                endpoint = db.query(APIEndpoint).filter(APIEndpoint.url == config.url).first()
                if endpoint and not endpoint.status:
                    return {
                        "status": False,  # Mark as down since endpoint is disabled
                        "url": url,
                        "status_code": 503,  # Service Unavailable - endpoint is disabled
                        "response_time": time.time() - start_time,
                        "is_disabled": True,  # Flag to indicate endpoint is disabled
                        "message": "Endpoint is disabled by user",
                        "is_error": False  # Not an error, just disabled
                    }
            
            async with getattr(self.session, config.method.value.lower())(
                url,
                headers=headers,
                json=config.request_body if config.request_body else None
            ) as response:
                response_time = time.time() - start_time
                status = response.status == config.expected_status
                
                try:
                    response_data = await response.json()
                except:
                    response_data = None
                
                return {
                    "status": status,
                    "url": url,
                    "status_code": response.status,
                    "response_time": response_time,
                    "response_data": response_data,
                    "is_disabled": False,  # Endpoint is enabled
                    "is_error": not status  # True if status check failed
                }
        except Exception as e:
            logger.error(f"Error checking endpoint {config.url}: {e}")
            return {
                "status": False,
                "url": config.url,
                "error": str(e),
                "is_disabled": False,  # This is an actual error, not a disabled endpoint
                "is_error": True  # This is an actual error
            }
    
    async def check_all_main_endpoints(self, batch_size: int = 5) -> List[Dict[str, Any]]:
        """Check all main system endpoints (APIEndpoint) in batches."""
        if not self._is_initialized:
            logger.error("Health checker not initialized")
            return [{"status": False, "error": "Health checker not initialized"}]
        results = []
        with get_db_session() as db:
            main_endpoints = db.query(APIEndpoint).all()
            # Fetch all discovered endpoints for matching
            discovered_endpoints = db.query(DiscoveredEndpoint).all()
            # Build lookup by (path, method)
            discovered_lookup = {(de.path, de.method): de for de in discovered_endpoints}
        endpoints_to_check = []
        for endpoint in main_endpoints:
            config = {
                'url': endpoint.url,
                'method': endpoint.method,
                'endpoint_id': endpoint.endpoint_id,
                'name': endpoint.name or endpoint.url,
                'is_discovered': False
            }
            endpoints_to_check.append(config)
        logger.info(f"Will check {len(endpoints_to_check)} main endpoints")
        for i in range(0, len(endpoints_to_check), batch_size):
            batch = endpoints_to_check[i:i + batch_size]
            tasks = [self.check_endpoint_from_db(config) for config in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            # Save results to database (if you want to save to a different table, adjust here)
            with get_db_session() as db:
                try:
                    for result, config in zip(batch_results, batch):
                        if 'url' in result:
                            status_code = result.get('status_code')
                            is_healthy = status_code is not None and 200 <= status_code < 400
                            # Find discovered_endpoint_id by matching path and method
                            discovered_ep = discovered_lookup.get((config['url'], config['method']))
                            discovered_endpoint_id = discovered_ep.id if discovered_ep else None
                            health_record = EndpointHealth(
                                discovered_endpoint_id=discovered_endpoint_id,  # Set if found, else None
                                status=result.get('status', False),
                                is_healthy=is_healthy,
                                response_time=result.get('response_time', 0),
                                checked_at=datetime.now(),
                                status_code=status_code,
                                error_message=result.get('error_message'),
                                failure_reason=result.get('failure_reason')
                            )
                            db.add(health_record)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error saving main endpoint health check results: {e}")
                    db.rollback()
        return results

    async def check_all_discovered_endpoints(self, remote_server_id: int, batch_size: int = 5) -> List[Dict[str, Any]]:
        """Check all discovered endpoints for a specific remote server in batches."""
        if not self._is_initialized:
            logger.error("Health checker not initialized")
            return [{"status": False, "error": "Health checker not initialized"}]
        results = []
        with get_db_session() as db:
            discovered_endpoints = db.query(DiscoveredEndpoint).filter(
                DiscoveredEndpoint.is_active == True,
                DiscoveredEndpoint.remote_server_id == remote_server_id
            ).all()
            logger.info(f"Found {len(discovered_endpoints)} discovered endpoints for remote server {remote_server_id} to check")
            main_endpoints = db.query(APIEndpoint).all()
            main_lookup = {(e.url, e.method): e for e in main_endpoints}
        endpoints_to_check = []
        for endpoint in discovered_endpoints:
            main = main_lookup.get((endpoint.path, endpoint.method))
            config = {
                'url': endpoint.path,
                'method': endpoint.method,
                'endpoint_id': endpoint.id,
                'name': endpoint.description or endpoint.path,
                'is_discovered': True,
                'main_endpoint_id': main.endpoint_id if main else None
            }
            endpoints_to_check.append(config)
        logger.info(f"Will check {len(endpoints_to_check)} discovered endpoints for remote server {remote_server_id}")
        for i in range(0, len(endpoints_to_check), batch_size):
            batch = endpoints_to_check[i:i + batch_size]
            tasks = [self.check_endpoint_from_db(config) for config in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            with get_db_session() as db:
                try:
                    for result, config in zip(batch_results, batch):
                        if 'url' in result:
                            status_code = result.get('status_code')
                            is_healthy = status_code is not None and 200 <= status_code < 400
                            health_record = EndpointHealth(
                                discovered_endpoint_id=config['endpoint_id'],
                                status=result.get('status', False),
                                is_healthy=is_healthy,
                                response_time=result.get('response_time', 0),
                                checked_at=datetime.now(),
                                status_code=status_code,
                                error_message=result.get('error_message'),
                                failure_reason=result.get('failure_reason')
                            )
                            db.add(health_record)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error saving discovered endpoint health check results: {e}")
                    db.rollback()
        return results

    async def check_endpoint_from_db(self, config: dict) -> Dict[str, Any]:
        """Check a single endpoint from database config"""
        if not self._is_initialized:
            logger.error("Health checker not initialized")
            return {"status": False, "error": "Health checker not initialized"}
            
        if not self.session or self.session.closed:
            logger.error("Session is closed or not initialized")
            return {"status": False, "error": "Session is closed or not initialized"}
            
        start_time = time.time()
        logger.info(f"Starting health check for endpoint {config['endpoint_id']}: {config['url']}")
        
        try:
            # For discovered endpoints, the URL might already be a full URL
            url = config['url'] if config['url'].startswith(('http://', 'https://')) else self._get_full_url(config['url'])
            logger.info(f"Full URL: {url}")
            
            # Prepare headers
            headers = self._prepare_headers(None)  # Pass None since we're not using EndpointConfig
            logger.info(f"Headers: {headers}")
            
            # Make the request
            method = config['method'].lower()
            request_kwargs = {
                "url": url,
                "headers": headers,
                "timeout": 30  # Use aiohttp's built-in timeout
            }
            
            # Handle different HTTP methods
            if method == 'get':
                # For GET requests, add query parameters if needed
                if '{' in url:  # If URL contains path parameters
                    # Replace path parameters with test values
                    url = url.replace('{matric_no}', 'A123456')
                    request_kwargs["url"] = url
            elif method in ['post', 'put', 'patch']:
                if 'token' in config['url'].lower() or 'login' in config['url'].lower():
                    # For authentication endpoints, use FormData instead of JSON
                    form_data = FormData()
                    form_data.add_field('grant_type', 'password')
                    form_data.add_field('username', 'health_check_user')
                    form_data.add_field('password', 'test_password')
                    
                    # Remove Content-Type header to let aiohttp set it for FormData
                    if 'Content-Type' in headers:
                        del headers['Content-Type']
                    
                    request_kwargs["data"] = form_data
            
            logger.info(f"Making {method.upper()} request to {url}")
            
            try:
                async with getattr(self.session, method)(**request_kwargs) as response:
                    response_time = time.time() - start_time
                    # Get response body for debugging and error extraction
                    backend_error = None
                    try:
                        response_body = await response.text()
                        logger.debug(f"Response body: {response_body[:500]}...")  # Log first 500 chars
                        try:
                            response_json = await response.json()
                            backend_error = response_json.get("detail") or response_json.get("error")
                        except Exception:
                            backend_error = None
                    except Exception:
                        response_body = None
                        backend_error = None
                    # Consider 2xx and 3xx status codes as successful
                    status = 200 <= response.status < 400
                    # Determine failure reason based on status code
                    failure_reason = self._get_failure_reason(response.status)
                    logger.info(f"Health check result for {config['url']}: status_code={response.status}, response_time={response_time:.3f}s, success={status}, failure_reason={failure_reason}")
                    error_message = backend_error or f"HTTP {response.status}: {self._get_status_description(response.status)}"
                    return {
                        "status": status,
                        "url": url,
                        "status_code": response.status,
                        "response_time": response_time,
                        "is_disabled": False,
                        "is_error": not status,
                        "failure_reason": failure_reason,
                        "error_message": error_message
                    }
            except asyncio.TimeoutError:
                logger.error(f"Timeout checking endpoint {config['url']}")
                return {
                    "status": False,
                    "url": config['url'],
                    "error": "Request timed out",
                    "is_disabled": False,
                    "is_error": True,
                    "failure_reason": "timeout",
                    "error_message": "Request timed out after 30 seconds"
                }
        except Exception as e:
            logger.error(f"Error checking endpoint {config['url']}: {e}")
            return {
                "status": False,
                "url": config['url'],
                "error": str(e),
                "is_disabled": False,
                "is_error": True,
                "failure_reason": "connection_error",
                "error_message": f"Connection failed: {str(e)}"
            }
    
    def _get_failure_reason(self, status_code: int) -> str:
        """Categorize failure reasons based on HTTP status codes"""
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
    
    def _get_status_description(self, status_code: int) -> str:
        """Get human-readable description for HTTP status codes"""
        descriptions = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return descriptions.get(status_code, f"Status {status_code}")

# Create a singleton instance
health_checker = EnhancedHealthChecker() 