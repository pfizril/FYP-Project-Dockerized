#!/usr/bin/env python
"""
Debug script to test health checker and verify error details are saved
"""
import asyncio
import sys
import os
from datetime import datetime
from database import session
from models import EndpointHealth, APIEndpoint

async def debug_health_check():
    """Debug the health checker to see if error details are saved"""
    try:
        # Import the health checker
        from enhanced_health_check import health_checker
        
        print("Initializing health checker...")
        await health_checker.initialize()
        
        if not health_checker._is_initialized:
            print("✗ Health checker failed to initialize")
            return
        
        print("✓ Health checker initialized")
        
        # Check a few endpoints manually
        with session() as db:
            endpoints = db.query(APIEndpoint).filter(
                APIEndpoint.status == True
            ).limit(3).all()
            
            print(f"Found {len(endpoints)} endpoints to test")
            
            for endpoint in endpoints:
                print(f"\nTesting endpoint: {endpoint.name} ({endpoint.url})")
                
                # Create a test config
                config = {
                    'url': endpoint.url,
                    'method': endpoint.method,
                    'endpoint_id': endpoint.endpoint_id,
                    'name': endpoint.name
                }
                
                # Check the endpoint
                result = await health_checker.check_endpoint_from_db(config)
                print(f"Result: {result}")
                
                # Save to database
                try:
                    health_record = EndpointHealth(
                        endpoint_id=config['endpoint_id'],
                        status=result.get('status', False),
                        response_time=result.get('response_time', 0),
                        checked_at=datetime.now(),
                        status_code=result.get('status_code'),
                        error_message=result.get('error_message'),
                        failure_reason=result.get('failure_reason')
                    )
                    
                    print(f"Creating health record with:")
                    print(f"  - status_code: {health_record.status_code}")
                    print(f"  - error_message: {health_record.error_message}")
                    print(f"  - failure_reason: {health_record.failure_reason}")
                    
                    db.add(health_record)
                    db.commit()
                    
                    print("✓ Health record saved")
                    
                    # Verify it was saved with all fields
                    saved_record = db.query(EndpointHealth).filter(
                        EndpointHealth.endpoint_health_id == health_record.endpoint_health_id
                    ).first()
                    
                    if saved_record:
                        print(f"✓ Verified saved record:")
                        print(f"  - status_code: {saved_record.status_code}")
                        print(f"  - error_message: {saved_record.error_message}")
                        print(f"  - failure_reason: {saved_record.failure_reason}")
                    else:
                        print("✗ Could not find saved record")
                        
                except Exception as e:
                    print(f"✗ Error saving health record: {e}")
                    db.rollback()
        
        await health_checker.close()
        print("\n✓ Debug completed")
        
    except Exception as e:
        print(f"✗ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_health_check()) 