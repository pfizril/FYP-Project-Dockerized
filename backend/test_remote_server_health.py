#!/usr/bin/env python
"""
Test script for remote server health scanning using the dedicated RemoteServerScanner
"""
import asyncio
import logging
import sys
from datetime import datetime
import json
from remote_server_scanner import RemoteServerScanner
from database import get_db_session
from models import RemoteServer, DiscoveredEndpoint

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("test_remote_health.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_remote_health")

async def test_remote_server_health(server_id: int):
    """Test health scanning for a specific remote server using the dedicated scanner"""
    logger.info(f"Starting remote server health test for server ID: {server_id}")
    
    try:
        # Get remote server details
        with get_db_session() as db:
            remote_server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
            if not remote_server:
                logger.error(f"Remote server {server_id} not found")
                return None
            
            logger.info(f"Remote server details:")
            logger.info(f"  Base URL: {remote_server.base_url}")
            logger.info(f"  Auth Type: {remote_server.auth_type}")
            logger.info(f"  Username: {remote_server.username}")
            
            # Initialize scanner
            scanner = RemoteServerScanner()
            
            # Set up authentication based on server type
            if remote_server.auth_type == "basic":
                basic_auth = (remote_server.username, remote_server.password)
                await scanner.initialize(base_url=remote_server.base_url, basic_auth=basic_auth)
            else:
                await scanner.initialize(base_url=remote_server.base_url)
            
            # Get discovered endpoints for this server
            discovered_endpoints = db.query(DiscoveredEndpoint).filter(
                DiscoveredEndpoint.remote_server_id == server_id,
                DiscoveredEndpoint.is_active == True
            ).all()
            
            logger.info(f"Found {len(discovered_endpoints)} active discovered endpoints")
            
            # Run health checks
            results = await scanner.scan_remote_server(server_id)
            
            # Calculate metrics
            total_requests = len(results)
            successful_requests = sum(1 for r in results if r.get('status', False))
            failed_requests = total_requests - successful_requests
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Prepare test results
            test_results = {
                "status": "success",
                "server": remote_server.name or f"Remote Server {server_id}",
                "discovered_endpoints": len(discovered_endpoints),
                "stored_endpoints": len(discovered_endpoints),
                "monitoring_results": [
                    {
                        "endpoint": r.get('url', ''),
                        "status": "success" if r.get('status', False) else "error",
                        "response_time": r.get('response_time', 0)
                    }
                    for r in results
                ],
                "metrics": {
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                    "failed_requests": failed_requests,
                    "success_rate": success_rate,
                    "average_response_time": sum(r.get('response_time', 0) for r in results) / total_requests if total_requests > 0 else 0,
                    "failure_breakdown": {}
                },
                "endpoints": [
                    {
                        "id": endpoint.id,
                        "path": endpoint.path,
                        "method": endpoint.method,
                        "status": "healthy" if any(r.get('status', False) and r.get('url', '').endswith(endpoint.path) for r in results) else "unhealthy",
                        "last_checked": datetime.now().isoformat(),
                        "response_time": next((r.get('response_time', 0) for r in results if r.get('url', '').endswith(endpoint.path)), 0),
                        "status_code": next((r.get('status_code', 0) for r in results if r.get('url', '').endswith(endpoint.path)), 0),
                        "failure_reason": next((r.get('failure_reason', 'unknown_error') for r in results if r.get('url', '').endswith(endpoint.path)), 'unknown_error')
                    }
                    for endpoint in discovered_endpoints
                ]
            }
            
            # Calculate failure breakdown
            failure_reasons = {}
            for result in results:
                if not result.get('status', False):
                    reason = result.get('failure_reason', 'unknown_error')
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            test_results["metrics"]["failure_breakdown"] = failure_reasons
            
            # Save results to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"remote_server_test_results_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(test_results, f, indent=2)
            
            logger.info(f"Test results saved to {filename}")
            
            # Log summary
            logger.info(f"Test completed:")
            logger.info(f"  Total endpoints: {total_requests}")
            logger.info(f"  Successful: {successful_requests}")
            logger.info(f"  Failed: {failed_requests}")
            logger.info(f"  Success rate: {success_rate:.2f}%")
            
            return test_results
            
    except Exception as e:
        logger.error(f"Error in remote server health test: {e}")
        return None
    finally:
        if 'scanner' in locals():
            await scanner.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_remote_server_health.py <server_id>")
        sys.exit(1)
    
    try:
        server_id = int(sys.argv[1])
        asyncio.run(test_remote_server_health(server_id))
    except ValueError:
        print("Error: server_id must be an integer")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 