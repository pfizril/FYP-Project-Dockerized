import asyncio
import logging
from database import get_db_session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
from api_discovery_service import APIDiscoveryService
from endpoint_monitoring_service import EndpointMonitoringService
from remote_server_service import RemoteServerService
import json
from datetime import datetime
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='discovered_endpoints_test.log'
)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def test_discovery_and_monitoring():
    """Test the discovery and monitoring of endpoints"""
    monitoring_service = None
    db = None
    
    try:
        db = get_db_session().__enter__()
        
        # Get a test remote server
        test_server = db.query(RemoteServer).first()
        if not test_server:
            logger.error("No remote server found in database. Please add a test server first.")
            return {
                "status": "error",
                "message": "No remote server found in database"
            }
        
        logger.info(f"Testing with server: {test_server.name} ({test_server.base_url})")
        
        # Initialize services
        discovery_service = APIDiscoveryService(db, test_server)
        monitoring_service = EndpointMonitoringService(db, test_server)
        remote_service = RemoteServerService(db)
        
        # Test endpoint discovery
        logger.info("Testing endpoint discovery...")
        discovered_endpoints = await discovery_service.discover_endpoints()
        logger.info(f"Discovered {len(discovered_endpoints)} endpoints")
        
        if not discovered_endpoints:
            return {
                "status": "error",
                "message": "No endpoints discovered"
            }
        
        # Store discovered endpoints
        logger.info("Storing discovered endpoints...")
        await discovery_service.store_discovered_endpoints(discovered_endpoints)
        db.commit()  # Ensure endpoints are saved
        
        # Verify stored endpoints
        stored_endpoints = db.query(DiscoveredEndpoint).filter(
            DiscoveredEndpoint.remote_server_id == test_server.id
        ).all()
        logger.info(f"Stored {len(stored_endpoints)} endpoints in database")
        
        # Test endpoint monitoring
        logger.info("Testing endpoint monitoring...")
        monitoring_results = []
        for endpoint in stored_endpoints:
            try:
                health_result = await monitoring_service.monitor_endpoint(endpoint)
                monitoring_results.append({
                    "endpoint": endpoint.path,
                    "status": health_result["status"]
                })
                logger.info(f"Monitored endpoint {endpoint.path}: {health_result['status']}")
                
                # Verify health record was saved
                health_record = db.query(EndpointHealth).filter(
                    EndpointHealth.discovered_endpoint_id == endpoint.id
                ).order_by(EndpointHealth.checked_at.desc()).first()
                
                if health_record:
                    logger.info(f"Health record saved for {endpoint.path}: status={health_record.status}")
                else:
                    logger.warning(f"No health record found for {endpoint.path}")
                
            except Exception as e:
                logger.error(f"Failed to monitor endpoint {endpoint.path}: {str(e)}")
                monitoring_results.append({
                    "endpoint": endpoint.path,
                    "status": "error",
                    "error": str(e)
                })
        
        db.commit()  # Ensure all health records are saved
        
        # Test remote server service
        logger.info("Testing remote server service...")
        result = await remote_service.discover_and_monitor(test_server.id)
        logger.info(f"Discovery and monitoring result: {result['status']}")
        
        # Get server metrics
        metrics = await remote_service.get_server_metrics(test_server.id)
        logger.info(f"Server metrics: {json.dumps(metrics, indent=2, cls=DateTimeEncoder)}")
        
        # Get server endpoints with health status
        endpoints = await remote_service.get_server_endpoints(test_server.id)
        logger.info(f"Server endpoints: {json.dumps(endpoints, indent=2, cls=DateTimeEncoder)}")
        
        return {
            "status": "success",
            "server": test_server.name,
            "discovered_endpoints": len(discovered_endpoints),
            "stored_endpoints": len(stored_endpoints),
            "monitoring_results": monitoring_results,
            "metrics": metrics,
            "endpoints": endpoints
        }
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        if db:
            db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        if monitoring_service:
            await monitoring_service.close()
        if db:
            db.close()

def main():
    """Run the tests"""
    logger.info("Starting discovered endpoints test...")
    result = asyncio.run(test_discovery_and_monitoring())
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"discovered_endpoints_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, cls=DateTimeEncoder)
    
    logger.info(f"Test results saved to {filename}")
    
    if result["status"] == "success":
        logger.info("Test completed successfully!")
    else:
        logger.error(f"Test failed: {result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main() 