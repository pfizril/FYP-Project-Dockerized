#!/usr/bin/env python
"""
Create test data for health monitoring
"""
import logging
from database import get_db_session
from models import Users, APIKey, APIEndpoint
import secrets
import string
from datetime import datetime
from auth import bcrypt_context

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test data for health monitoring"""
    with get_db_session() as db:
        try:
            # Create test user with properly hashed password
            test_password = "test_password"
            hashed_password = bcrypt_context.hash(test_password)
            
            test_user = Users(
                user_name="health_check_user",
                user_role="Admin",
                user_email="health_check@example.com",
                hashed_psw=hashed_password
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            logger.info(f"Created test user with ID: {test_user.user_id}")
            
            # Create API key
            api_key = APIKey(
                key=f"health-monitor-key-{secrets.token_hex(8)}",
                user_id=test_user.user_id
            )
            db.add(api_key)
            db.commit()
            db.refresh(api_key)
            logger.info(f"Created API key with ID: {api_key.key_id}")
            logger.info(f"API Key: {api_key.key}")
            
            # Create test endpoint
            test_endpoint = APIEndpoint(
                name="Health Check Test Endpoint",
                url=f"/test/health-check-{secrets.token_hex(4)}",
                method="GET",
                status=True,
                description="Test endpoint for health monitoring",
                requires_auth=False
            )
            db.add(test_endpoint)
            db.commit()
            db.refresh(test_endpoint)
            logger.info(f"Created test endpoint with ID: {test_endpoint.endpoint_id}")
            logger.info(f"Endpoint URL: {test_endpoint.url}")
            
            # Save IDs to a file for reference
            with open("test_data_ids.txt", "w") as f:
                f.write(f"User ID: {test_user.user_id}\n")
                f.write(f"API Key ID: {api_key.key_id}\n")
                f.write(f"Endpoint ID: {test_endpoint.endpoint_id}\n")
                f.write(f"API Key: {api_key.key}\n")
                f.write(f"Endpoint URL: {test_endpoint.url}\n")
            
            return {
                "user_id": test_user.user_id,
                "key_id": api_key.key_id,
                "endpoint_id": test_endpoint.endpoint_id,
                "api_key": api_key.key,
                "endpoint_url": test_endpoint.url
            }
            
        except Exception as e:
            logger.error(f"Error creating test data: {e}")
            db.rollback()
            raise

if __name__ == "__main__":
    create_test_data() 