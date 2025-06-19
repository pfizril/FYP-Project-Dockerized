from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime
from create_test_data import create_test_data

class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"

@dataclass
class EndpointConfig:
    """Configuration for endpoint health checks"""
    url: str
    method: HTTPMethod
    required_headers: Dict[str, str] = None
    request_body: Dict[str, Any] = None
    expected_status: int = 200
    timeout: int = 5
    retry_count: int = 3
    retry_delay: int = 1
    validate_response: bool = True
    response_schema: Dict[str, Any] = None

class EndpointConfigManager:
    """Manages endpoint configurations for health checks"""
    
    def __init__(self):
        self.configs: Dict[str, EndpointConfig] = {}
        self._test_data = None
        self._load_configs()
    
    def _load_configs(self):
        """Load endpoint configurations from environment or defaults"""
        # Get fresh test data
        self._test_data = create_test_data()
        
        # Common headers for all endpoints
        common_headers = {
            "X-API-KEY": "GiVP9pAcIF7cueDii3eV1p1e__mB751g9T2qCUV9C6w",  # Global health check API key
            "Content-Type": "application/json",
            "X-Health-Check": "true"
        }

        # Auth endpoints
        self.configs.update({
            "/auth/token": EndpointConfig(
                url="/auth/token",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                request_body={
                    "username": "health_check_user",
                    "password": "test_password",
                    "grant_type": "password"
                },
                validate_response=False,
                expected_status=422  # optional
            ),
            "/auth/current-user": EndpointConfig(
                url="/auth/current-user",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/update-user": EndpointConfig(
                url="/auth/update-user",
                method=HTTPMethod.PUT,
                required_headers=common_headers,
                request_body={
                    "username": "health_check_user",
                    "email": "health_check@example.com"
                },
                expected_status=200
            ),
            "/auth/users/create-user": EndpointConfig(
                url="/auth/users/create-user",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                request_body={
                    "user_name": "test_user_health",
                    "user_psw": "test123",
                    "user_email": "test@example.com",
                    "user_role": "User"
                },
                expected_status=201
            ),
            "/auth/users/list": EndpointConfig(
                url="/auth/users/list",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/api-keys/generate/{user_id}": EndpointConfig(
                url=f"/auth/api-keys/generate/{self._test_data['user_id']}",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                expected_status=201
            ),
            "/auth/api-keys/revoke/{key_id}": EndpointConfig(
                url=f"/auth/api-keys/revoke/{self._test_data['key_id']}",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/api-keys/list": EndpointConfig(
                url="/auth/api-keys/list",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/api-keys/{user_id}": EndpointConfig(
                url=f"/auth/api-keys/{self._test_data['user_id']}",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/protected": EndpointConfig(
                url="/auth/protected",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/users/update-role/{user_id}": EndpointConfig(
                url=f"/auth/users/update-role/{self._test_data['user_id']}?new_role=Admin",
                method=HTTPMethod.PUT,
                required_headers=common_headers,
                expected_status=200
            ),
            "/auth/show-current-users": EndpointConfig(
                url="/auth/show-current-users",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            )
        })

        # API Management endpoints
        self.configs.update({
            "/api-management/endpoints/create": EndpointConfig(
                url="/api-management/endpoints/create",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                request_body={
                    "name": "Test Endpoint",
                    "url": "/test/endpoint",
                    "method": "GET",
                    "description": "Test endpoint for health monitoring",
                    "status": True,
                    "requires_auth": True
                },
                expected_status=201
            ),
            "/api-management/endpoints": EndpointConfig(
                url="/api-management/endpoints",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/api-management/endpoints-update/{endpoint_id}": EndpointConfig(
                url=f"/api-management/endpoints-update/{self._test_data['endpoint_id']}",
                method=HTTPMethod.PUT,
                required_headers=common_headers,
                request_body={
                    "name": "Updated Test Endpoint",
                    "description": "Updated test endpoint"
                },
                expected_status=200
            ),
            "/api-management/delete-endpoints/{endpoint_id}": EndpointConfig(
                url=f"/api-management/delete-endpoints/{self._test_data['endpoint_id']}",
                method=HTTPMethod.DELETE,
                required_headers=common_headers,
                expected_status=200
            ),
            "/api-management/endpoints/toggle_status/{endpoint_id}": EndpointConfig(
                url=f"/api-management/endpoints/toggle_status/{self._test_data['endpoint_id']}?status=true",
                method=HTTPMethod.PUT,
                required_headers=common_headers,
                expected_status=200
            )
        })

        # Analytics endpoints
        self.configs.update({
            "/analytics/traffic-insights": EndpointConfig(
                url="/analytics/traffic-insights",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/success-failure-rates": EndpointConfig(
                url="/analytics/success-failure-rates",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/response-time-analysis": EndpointConfig(
                url="/analytics/response-time-analysis",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/endpoints/health-summary": EndpointConfig(
                url="/analytics/endpoints/health-summary",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/export-logs": EndpointConfig(
                url="/analytics/export-logs",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/overview-metrics": EndpointConfig(
                url="/analytics/overview-metrics",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/requests-breakdown": EndpointConfig(
                url="/analytics/requests-breakdown",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/failures-breakdown": EndpointConfig(
                url="/analytics/failures-breakdown",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/performance-trends": EndpointConfig(
                url="/analytics/performance-trends",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/analytics/client-insights": EndpointConfig(
                url="/analytics/client-insights",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            )
        })

        # Security endpoints
        self.configs.update({
            "/security/vulnerability-scan/comprehensive": EndpointConfig(
                url="/security/vulnerability-scan/comprehensive",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/security/traffic-analysis": EndpointConfig(
                url="/security/traffic-analysis",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/security/threat-score": EndpointConfig(
                url="/security/threat-score",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/security/vulnerability-scan/open-endpoints": EndpointConfig(
                url="/security/vulnerability-scan/open-endpoints",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/security/vulnerability-scan/cors": EndpointConfig(
                url="/security/vulnerability-scan/cors",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            )
        })

        # CSRF endpoints
        self.configs.update({
            "/csrf/csrf-token": EndpointConfig(
                url="/csrf/csrf-token",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/csrf/test-csrf-protection": EndpointConfig(
                url="/csrf/test-csrf-protection",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                request_body={"test": "data"},
                expected_status=200
            )
        })

        # Basic endpoints
        self.configs.update({
            "/health": EndpointConfig(
                url="/health",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200,
                validate_response=False  # Don't validate JSON response for health endpoint
            ),
            "/": EndpointConfig(
                url="/",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200,
                validate_response=False  # Don't validate JSON response for root endpoint
            ),
            "/admin-dashboard": EndpointConfig(
                url="/admin-dashboard",
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200
            ),
            "/test-payload": EndpointConfig(
                url="/test-payload",
                method=HTTPMethod.POST,
                required_headers=common_headers,
                request_body={"test": "data"},
                expected_status=200
            ),
            "/test/health-check": EndpointConfig(
                url=self._test_data['endpoint_url'],
                method=HTTPMethod.GET,
                required_headers=common_headers,
                expected_status=200,
                validate_response=False
            )
        })
    
    def get_config(self, endpoint_path: str) -> Optional[EndpointConfig]:
        """Get configuration for a specific endpoint"""
        # Try exact match first
        if endpoint_path in self.configs:
            return self.configs[endpoint_path]
        
        # Try pattern matching for dynamic routes
        for path, config in self.configs.items():
            if path.replace("{endpoint_id}", "1").replace("{user_id}", "1").replace("{key_id}", "1") == endpoint_path:
                return config
        
        return None
    
    def update_config(self, endpoint_path: str, config: EndpointConfig):
        """Update configuration for an endpoint"""
        self.configs[endpoint_path] = config
    
    def remove_config(self, endpoint_path: str):
        """Remove configuration for an endpoint"""
        if endpoint_path in self.configs:
            del self.configs[endpoint_path]
    
    def get_all_configs(self) -> Dict[str, EndpointConfig]:
        """Get all endpoint configurations"""
        return self.configs.copy()

# Create a singleton instance
endpoint_config_manager = EndpointConfigManager() 