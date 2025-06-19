import asyncio
import logging
from sqlalchemy.orm import Session
from database import get_db_session
from models import RemoteServer
from remote_server_service import RemoteServerService
from remote_auth_service import RemoteAuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_remote_server():
    """Test remote server monitoring functionality."""
    db = None
    service = None
    test_server = None
    
    try:
        # Get database session
        db = get_db_session().__enter__()
        
        # Create a test remote server
        test_server = RemoteServer(
            name="Test Remote API",
            base_url="http://localhost:8000",  # Your local FastAPI server
            description="Test server for monitoring",
            auth_type="basic",
            username="fizril2001",
            password="fizril2001",
            health_check_url="/health",
            is_active=True
        )
        db.add(test_server)
        db.commit()
        db.refresh(test_server)
        
        logger.info(f"Created test server with ID: {test_server.id}")
        
        # Create service
        service = RemoteServerService(db)
        
        # Test server validation
        logger.info("Testing server validation...")
        validation_result = await service.validate_server(test_server.base_url)
        logger.info(f"Validation result: {validation_result}")
        
        # Test server status update
        logger.info("Testing server status update...")
        await service.update_server_status(test_server)
        logger.info(f"Server status: {test_server.status}")
        
        # Test analytics
        logger.info("Testing analytics...")
        analytics = await service.get_server_analytics(test_server.id)
        logger.info(f"Analytics: {analytics}")
        
        # Test endpoints
        logger.info("Testing endpoint discovery...")
        endpoints = await service.get_endpoints(test_server.id)
        logger.info(f"Endpoints: {endpoints}")
        
        # Test threat logs
        logger.info("Testing threat logs...")
        threat_logs = await service.get_threat_logs(test_server.id)
        logger.info(f"Threat logs: {threat_logs}")
        
        # Test traffic logs
        logger.info("Testing traffic logs...")
        traffic_logs = await service.get_traffic_logs(test_server.id)
        logger.info(f"Traffic logs: {traffic_logs}")
        
        # Test vulnerability scans
        logger.info("Testing vulnerability scans...")
        vuln_scans = await service.get_vulnerability_scans(test_server.id)
        logger.info(f"Vulnerability scans: {vuln_scans}")
        
        # Test activity logs
        logger.info("Testing activity logs...")
        activity_logs = await service.get_activity_logs(test_server.id)
        logger.info(f"Activity logs: {activity_logs}")
        
        # Test rate limits
        logger.info("Testing rate limits...")
        rate_limits = await service.get_rate_limits(test_server.id)
        logger.info(f"Rate limits: {rate_limits}")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        raise
    finally:
        # Clean up resources
        if service and service.client:
            await service.client.aclose()
        
        if db and test_server:
            try:
                db.delete(test_server)
                db.commit()
                logger.info("Cleaned up test server")
            except Exception as e:
                logger.error(f"Error cleaning up test server: {str(e)}")
        
        if db:
            try:
                db.close()
                logger.info("Closed database session")
            except Exception as e:
                logger.error(f"Error closing database session: {str(e)}")

async def main():
    """Main test function."""
    await test_remote_server()

if __name__ == "__main__":
    asyncio.run(main()) 