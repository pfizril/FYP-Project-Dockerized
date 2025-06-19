import asyncio
import logging
from database import get_db_session
from models import RemoteServer, DiscoveredEndpoint, EndpointHealth
from api_discovery_service import APIDiscoveryService
from endpoint_monitoring_service import EndpointMonitoringService
from remote_server_service import RemoteServerService
import json
from datetime import datetime
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='system_test.log'
)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def test_system():
    """Test the entire endpoint discovery and monitoring system"""
    monitoring_service = None
    db = None
    
    try:
        db = get_db_session().__enter__()
        
        # Step 1: Create a test remote server if none exists
        test_server = db.query(RemoteServer).first()
        if not test_server:
            logger.info("Creating test remote server...")
            test_server = RemoteServer(
                name="Test API Server",
                base_url="http://localhost:8000",  # Update this to your test server URL
                description="Test server for endpoint discovery and monitoring",
                status="offline",
                auth_type="basic",
                username="test",  # Update with your test credentials
                password="test",  # Update with your test credentials
                is_active=True,
                created_by=1  # Update with a valid user ID
            )
            db.add(test_server)
            db.commit()
            logger.info(f"Created test server with ID: {test_server.id}")
        
        # Step 2: Initialize services
        logger.info("Initializing services...")
        discovery_service = APIDiscoveryService(db, test_server)
        monitoring_service = EndpointMonitoringService(db, test_server)
        remote_service = RemoteServerService(db)
        
        # Step 3: Test server validation
        logger.info("Testing server validation...")
        validation_result = await remote_service.validate_server(test_server.base_url)
        logger.info(f"Server validation result: {validation_result}")
        
        # Step 4: Discover endpoints
        logger.info("Discovering endpoints...")
        discovered_endpoints = await discovery_service.discover_endpoints()
        logger.info(f"Discovered {len(discovered_endpoints)} endpoints")
        
        if not discovered_endpoints:
            return {
                "status": "error",
                "message": "No endpoints discovered"
            }
        
        # Step 5: Store discovered endpoints
        logger.info("Storing discovered endpoints...")
        await discovery_service.store_discovered_endpoints(discovered_endpoints)
        db.commit()
        
        # Step 6: Verify stored endpoints
        stored_endpoints = db.query(DiscoveredEndpoint).filter(
            DiscoveredEndpoint.remote_server_id == test_server.id
        ).all()
        logger.info(f"Stored {len(stored_endpoints)} endpoints in database")
        
        # Step 7: Monitor endpoints
        logger.info("Monitoring endpoints...")
        monitoring_results = []
        for endpoint in stored_endpoints:
            try:
                health_result = await monitoring_service.monitor_endpoint(endpoint)
                monitoring_results.append({
                    "endpoint": endpoint.path,
                    "status": health_result["status"],
                    "response_time": health_result.get("response_time")
                })
                logger.info(f"Monitored endpoint {endpoint.path}: {health_result['status']}")
                
                # Verify health record
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
        
        db.commit()
        
        # Step 8: Get server metrics
        logger.info("Getting server metrics...")
        metrics = await remote_service.get_server_metrics(test_server.id)
        logger.info(f"Server metrics: {json.dumps(metrics, indent=2, cls=DateTimeEncoder)}")
        
        # Step 9: Get server endpoints with health status
        logger.info("Getting server endpoints with health status...")
        endpoints = await remote_service.get_server_endpoints(test_server.id)
        logger.info(f"Server endpoints: {json.dumps(endpoints, indent=2, cls=DateTimeEncoder)}")
        
        # Step 10: Test continuous monitoring
        logger.info("Testing continuous monitoring...")
        for _ in range(3):  # Monitor 3 times with 5-second intervals
            for endpoint in stored_endpoints:
                await monitoring_service.monitor_endpoint(endpoint)
            await asyncio.sleep(5)  # Wait 5 seconds between monitoring cycles
        
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
    """Run the system test"""
    logger.info("Starting system test...")
    result = asyncio.run(test_system())
    
    # Save test results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"system_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, cls=DateTimeEncoder)
    
    logger.info(f"Test results saved to {filename}")
    
    if result["status"] == "success":
        logger.info("System test completed successfully!")
    else:
        logger.error(f"System test failed: {result.get('message', 'Unknown error')}")

if __name__ == "__main__":
    main() 