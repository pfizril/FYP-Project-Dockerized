import httpx
import asyncio
import base64
import logging
import os
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get secret key from environment or use default for testing
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key")
ALGORITHM = "HS256"

def create_test_token():
    """Create a test JWT token."""
    expires = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {
        "sub": "fizril2001",
        "id": 1,
        "role": "Admin",
        "exp": expires
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def test_endpoint():
    """Test the analytics endpoint directly."""
    # Get API key from environment variable or use default
    api_key = os.getenv("API_KEY", "test-api-key")
    
    # Create JWT token
    token = create_test_token()
    
    # Set up headers with both API key and JWT token
    headers = {
        'Authorization': f'Bearer {token}',
        'X-API-KEY': api_key
    }
    
    try:
        # First test the health endpoint
        async with httpx.AsyncClient() as client:
            logger.info("Testing health endpoint...")
            health_response = await client.get("http://localhost:8000/health")
            logger.info(f"Health endpoint response: {health_response.status_code}")
            logger.info(f"Health endpoint content: {health_response.text}")
            
            # Then test the analytics endpoint
            logger.info("\nTesting analytics endpoint...")
            analytics_response = await client.get(
                "http://localhost:8000/analytics/summary",
                params={"time_range": "24h"},
                headers=headers
            )
            logger.info(f"Analytics endpoint response: {analytics_response.status_code}")
            logger.info(f"Analytics endpoint content: {analytics_response.text}")
            
    except Exception as e:
        logger.error(f"Error testing endpoint: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_endpoint()) 