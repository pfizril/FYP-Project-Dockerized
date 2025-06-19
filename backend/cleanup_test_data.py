#!/usr/bin/env python
"""
Clean up test data from the database
"""
import logging
from database import get_db_session
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_test_data():
    """Clean up all test data from the database"""
    with get_db_session() as db:
        try:
            # Delete in correct order to handle foreign key constraints
            
            # 1. Delete endpoint health records
            db.execute(text("""
                DELETE FROM endpoint_health 
                WHERE discovered_endpoint_id IN (
                    SELECT id FROM discovered_endpoints 
                    WHERE path LIKE '/test/health-check-%'
                )
            """))
            db.commit()
            logger.info("Deleted endpoint health records")
            
            # 2. Delete discovered endpoints
            db.execute(text("DELETE FROM discovered_endpoints WHERE path LIKE '/test/health-check-%'"))
            db.commit()
            logger.info("Deleted discovered endpoints")
            
            # 3. Delete activity logs for both test users
            db.execute(text("""
                DELETE FROM activity_logs 
                WHERE user_id IN (
                    SELECT user_id FROM "Users" 
                    WHERE user_email IN ('health_check@example.com', 'test@example.com')
                )
            """))
            db.commit()
            logger.info("Deleted activity logs")
            
            # 4. Delete ALL API keys for both test users
            db.execute(text("""
                DELETE FROM api_keys 
                WHERE user_id IN (
                    SELECT user_id FROM "Users" 
                    WHERE user_email IN ('health_check@example.com', 'test@example.com')
                )
            """))
            db.commit()
            logger.info("Deleted API keys")
            
            # 5. Delete endpoints
            db.execute(text("DELETE FROM api_endpoints WHERE url LIKE '/test/health-check-%'"))
            db.commit()
            logger.info("Deleted test endpoints")
            
            # 6. Finally delete both test users
            db.execute(text("""
                DELETE FROM "Users" 
                WHERE user_email IN ('health_check@example.com', 'test@example.com')
            """))
            db.commit()
            logger.info("Deleted test users")
            
            logger.info("Successfully cleaned up all test data")
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
            db.rollback()

if __name__ == "__main__":
    cleanup_test_data() 