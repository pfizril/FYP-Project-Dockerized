import httpx
import asyncio
import logging
from datetime import datetime
import json
from typing import Dict, Any
import os
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UMDataAPITester:
    def __init__(self):
        self.base_url = "https://data-api.um.edu.my"
        self.username = os.getenv("UM_USERNAME")
        self.password = os.getenv("UM_PASSWORD")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        # Add Basic Auth header
        self._update_auth_header()

    def _update_auth_header(self):
        """Update the Authorization header with Basic Auth credentials."""
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers["Authorization"] = f"Basic {encoded_credentials}"

    async def test_endpoint(self, endpoint: str, method: str = "GET", params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Test a specific endpoint with given parameters."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self.headers, json=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.content else None,
                    "headers": dict(response.headers)
                }
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            return {
                "status_code": e.response.status_code if hasattr(e, 'response') else 500,
                "error": str(e),
                "headers": dict(e.response.headers) if hasattr(e, 'response') else {}
            }
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return {
                "status_code": 500,
                "error": str(e)
            }

    async def test_all_endpoints(self):
        """Test all available endpoints."""
        test_results = {}

        # Test endpoints based on your backend API structure
        endpoints = [
            # Analytics endpoints
            "/api/v1/staff/public/staff/",  # Overview metrics
            # "/analytics/endpoints/latest-health",  # Endpoint health status
            # "/analytics/response-time-analysis",  # Response time analysis
           
        ]

        for endpoint in endpoints:
            logger.info(f"Testing endpoint: {endpoint}")
            # Replace {id} and {path} with test values
            test_endpoint = endpoint.replace("{id}", "1").replace("{path}", "test")
            result = await self.test_endpoint(test_endpoint)
            test_results[endpoint] = result
            logger.info(f"Result for {endpoint}: {json.dumps(result, indent=2)}")

        return test_results

async def main():
    """Main function to run the tests."""
    tester = UMDataAPITester()
    
    logger.info("Starting UM Data API tests...")
    logger.info(f"Using credentials - Username: {tester.username}")
    
    results = await tester.test_all_endpoints()
    
    # Save results to a file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"um_api_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test results saved to {filename}")
    
    # Print summary
    success_count = sum(1 for result in results.values() if result.get("status_code") == 200)
    total_count = len(results)
    
    logger.info(f"\nTest Summary:")
    logger.info(f"Total endpoints tested: {total_count}")
    logger.info(f"Successful tests: {success_count}")
    logger.info(f"Failed tests: {total_count - success_count}")

if __name__ == "__main__":
    asyncio.run(main()) 