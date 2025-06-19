from fastapi import APIRouter, Depends, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import case
import csv
from io import StringIO
from database import session
from models import APIRequest, EndpointHealth,APIEndpoint, ActivityLog, Users, DiscoveredEndpoint, RemoteServer
from dotenv import load_dotenv
import time
import os
import requests
import aiohttp
import logging
from typing import Annotated, Dict, List, Optional
from fastapi.security import APIKeyHeader
from auth import get_current_user
from datetime import datetime
import asyncio
from sqlalchemy import text
from api_health_scanner import run_remote_server_health_scan

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/analytics',
    tags=['API Analytics']
)

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()

db_dependency = Depends(get_db)
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get("/traffic-insights")
def traffic_insights(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = db_dependency):
    insights = db.query(
        APIRequest.endpoint, func.count(APIRequest.api_req_id).label("request_count")
    ).group_by(APIRequest.endpoint).all()

    return [
    {"endpoint": endpoint, "request_count": count}
    for endpoint, count in insights
    ]


@router.get("/success-failure-rates")
def success_failure_rates(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = db_dependency):
    rates = db.query(
        APIRequest.endpoint,
        func.count().label("total_requests"),
        func.sum(
            case(
                (APIRequest.status_code.between(200, 299), 1),
                else_=0
            )
        ).label("successful_requests")
    ).group_by(APIRequest.endpoint).all()

    response = []
    for endpoint, total, success in rates:
        response.append({
            "endpoint": endpoint,
            "total_requests": total,
            "success_rate": round((success / total) * 100, 2) if total > 0 else 0
        })
    return response

@router.get("/response-time-analysis")
def response_time_analysis(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = db_dependency):
    ignored_endpoints = ["/docs", "/openapi.json", "/favicon.ico"]

    response_times = db.query(
        APIRequest.endpoint, func.avg(APIRequest.response_time).label("avg_response_time")
    ).group_by(APIRequest.endpoint).all()

    # Exclude ignored endpoints
    result = [
        {"endpoint": endpoint, "avg_response_time": avg_time}
        for endpoint, avg_time in response_times if endpoint not in ignored_endpoints
    ]

    return {"response_times": result}

@router.get("/export-logs")
async def export_logs(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency
):
    output = None
    try:
        # Verify API key first
        if not api_key:
            raise HTTPException(status_code=401, detail="API key is required")
            
        # Log the export attempt
        # logging.info(f"Export API request logs received from user {user.get('user_id') if user else 'unknown'}")
        
        # Get all API requests ordered by timestamp
        api_requests = db.query(APIRequest).order_by(APIRequest.timestamp.desc()).all()
        
        if not api_requests:
            logging.warning("No API request logs found to export")
            raise HTTPException(status_code=404, detail="No API request logs found to export")
            
        logging.info(f"Found {len(api_requests)} API requests to export")
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers for API requests
        writer.writerow([
            "API Request ID",
            "Timestamp",
            "Endpoint",
            "Method",
            "Status Code",
            "Response Time (ms)",
            "Client IP"
        ])
        
        # Write data rows
        for request in api_requests:
            try:
                writer.writerow([
                    request.api_req_id,
                    request.timestamp.isoformat() if request.timestamp else "",
                    request.endpoint or "",
                    request.method or "",
                    request.status_code or "",
                    request.response_time or "",
                    request.client_ip or ""
                ])
            except Exception as row_error:
                logging.error(f"Error writing row for request {request.api_req_id}: {str(row_error)}")
                continue
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"api_request_logs_{timestamp}.csv"
        
        # Get the CSV content
        csv_content = output.getvalue()
        content_length = len(csv_content.encode('utf-8'))
        
        # logging.info(f"Generated CSV content, size: {content_length} bytes")
        
        # Create response with proper headers
        response = Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-API-KEY, Authorization"
            }
        )
        
        # logging.info(f"Successfully prepared export file: {filename}")
        return response
        
    except HTTPException as he:
        logging.error(f"HTTP Exception in export_logs: {str(he)}")
        raise
    except Exception as e:
        logging.error(f"Error exporting logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to export logs. Please try again later."
        )
    finally:
        if output:
            output.close()

@router.get("/export-health-logs")
async def export_health_logs(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency
):
    output = None
    try:
        # Verify API key first
        if not api_key:
            raise HTTPException(status_code=401, detail="API key is required")
            
        # Log the export attempt
        logging.info(f"Export health logs received from user {user.get('user_id') if user else 'unknown'}")
        
        # Get all endpoint health records with endpoint details ordered by checked_at
        health_records = db.query(
            EndpointHealth,
            APIEndpoint
        ).outerjoin(
            APIEndpoint,
            EndpointHealth.endpoint_id == APIEndpoint.endpoint_id
        ).order_by(
            EndpointHealth.checked_at.desc()
        ).all()
        
        if not health_records:
            logging.warning("No health logs found to export")
            raise HTTPException(status_code=404, detail="No health logs found to export")
            
        logging.info(f"Found {len(health_records)} health records to export")
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers for health records with endpoint details
        writer.writerow([
            "Health Record ID",
            "Endpoint ID",
            "Endpoint Name",
            "Endpoint URL",
            "HTTP Method",
            "Description",
            "Requires Auth",
            "Endpoint Status",
            "Health Status",
            "Response Time (ms)",
            "Checked At",
            "Endpoint Created At",
            "Endpoint Updated At"
        ])
        
        # Write data rows
        for record in health_records:
            try:
                health, endpoint = record
                writer.writerow([
                    health.endpoint_health_id,
                    health.endpoint_id or "",
                    endpoint.name if endpoint else "Unknown",
                    endpoint.url if endpoint else "Unknown",
                    endpoint.method if endpoint else "Unknown",
                    endpoint.description if endpoint else "",
                    "Yes" if endpoint and endpoint.requires_auth else "No",
                    "Active" if endpoint and endpoint.status else "Inactive",
                    "Healthy" if health.status else "Unhealthy",
                    health.response_time or "",
                    health.checked_at.isoformat() if health.checked_at else "",
                    endpoint.created_at.isoformat() if endpoint and endpoint.created_at else "",
                    endpoint.updated_at.isoformat() if endpoint and endpoint.updated_at else ""
                ])
            except Exception as row_error:
                logging.error(f"Error writing row for health record {health.endpoint_health_id}: {str(row_error)}")
                continue
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"health_logs_{timestamp}.csv"
        
        # Get the CSV content
        csv_content = output.getvalue()
        content_length = len(csv_content.encode('utf-8'))
        
        logging.info(f"Generated CSV content, size: {content_length} bytes")
        
        # Create response with proper headers
        response = Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-API-KEY, Authorization"
            }
        )
        
        logging.info(f"Successfully prepared export file: {filename}")
        return response
        
    except HTTPException as he:
        logging.error(f"HTTP Exception in export_health_logs: {str(he)}")
        raise
    except Exception as e:
        logging.error(f"Error exporting health logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to export health logs. Please try again later."
        )
    finally:
        if output:
            output.close()

@router.get("/remote-servers/{server_id}/export-health-logs")
async def export_remote_server_health_logs(
    server_id: int,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency
):
    output = None
    try:
        # Verify API key first
        if not api_key:
            raise HTTPException(status_code=401, detail="API key is required")
            
        # Log the export attempt
        logging.info(f"Export remote server health logs received from user {user.get('user_id') if user else 'unknown'} for server {server_id}")
        
        # Get remote server details
        remote_server = db.query(RemoteServer).filter(RemoteServer.id == server_id).first()
        if not remote_server:
            raise HTTPException(status_code=404, detail="Remote server not found")
        
        # Get all health records for discovered endpoints of this remote server
        health_records = db.query(
            EndpointHealth,
            DiscoveredEndpoint,
            RemoteServer
        ).join(
            DiscoveredEndpoint,
            EndpointHealth.discovered_endpoint_id == DiscoveredEndpoint.id
        ).join(
            RemoteServer,
            DiscoveredEndpoint.remote_server_id == RemoteServer.id
        ).filter(
            RemoteServer.id == server_id
        ).order_by(
            EndpointHealth.checked_at.desc()
        ).all()
        
        if not health_records:
            logging.warning(f"No health logs found to export for remote server {server_id}")
            raise HTTPException(status_code=404, detail="No health logs found for this remote server")
            
        logging.info(f"Found {len(health_records)} health records to export for remote server {server_id}")
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers for remote server health records
        writer.writerow([
            "Health Record ID",
            "Remote Server ID",
            "Remote Server Name",
            "Remote Server URL",
            "Discovered Endpoint ID",
            "Endpoint Path",
            "HTTP Method",
            "Endpoint Description",
            "Endpoint Active",
            "Health Status",
            "Response Time (ms)",
            "Status Code",
            "Error Message",
            "Failure Reason",
            "Checked At",
            "Endpoint Discovered At",
            "Last Checked"
        ])
        
        # Write data rows
        for record in health_records:
            try:
                health, endpoint, server = record
                writer.writerow([
                    health.endpoint_health_id,
                    server.id,
                    server.name,
                    server.base_url,
                    endpoint.id,
                    endpoint.path,
                    endpoint.method,
                    endpoint.description or "",
                    "Active" if endpoint.is_active else "Inactive",
                    "Healthy" if health.is_healthy else "Unhealthy",
                    health.response_time or "",
                    health.status_code or "",
                    health.error_message or "",
                    health.failure_reason or "",
                    health.checked_at.isoformat() if health.checked_at else "",
                    endpoint.discovered_at.isoformat() if endpoint.discovered_at else "",
                    endpoint.last_checked.isoformat() if endpoint.last_checked else ""
                ])
            except Exception as row_error:
                logging.error(f"Error writing row for health record {health.endpoint_health_id}: {str(row_error)}")
                continue
        
        # Generate filename with timestamp and server name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        server_name_safe = "".join(c for c in remote_server.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"remote_server_health_logs_{server_name_safe}_{timestamp}.csv"
        
        # Get the CSV content
        csv_content = output.getvalue()
        content_length = len(csv_content.encode('utf-8'))
        
        logging.info(f"Generated CSV content, size: {content_length} bytes")
        
        # Create response with proper headers
        response = Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
                "Access-Control-Expose-Headers": "Content-Disposition",
                "Content-Length": str(content_length),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, X-API-KEY, Authorization"
            }
        )
        
        logging.info(f"Successfully prepared export file: {filename}")
        return response
        
    except HTTPException as he:
        logging.error(f"HTTP Exception in export_remote_server_health_logs: {str(he)}")
        raise
    except Exception as e:
        logging.error(f"Error exporting remote server health logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to export remote server health logs. Please try again later."
        )
    finally:
        if output:
            output.close()

@router.get("/endpoints/health-summary")
async def get_health_summary(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    # Querying health data
    summary = db.query(
        EndpointHealth.status,
        func.count(EndpointHealth.endpoint_health_id).label("count"),
        func.avg(EndpointHealth.response_time).label("avg_response_time")
    ).group_by(EndpointHealth.status).all()

    # Format the result to return as a list of dictionaries
    result = [
        {
            "status": "up" if status else "down",
            "count": count,
            "avg_response_time": avg_response_time
        }
        for status, count, avg_response_time in summary
    ]
    
    return result

@router.get("/endpoints/latest-health")
async def get_latest_endpoint_health(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency, 
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    status_filter: str = "all",
    method_filter: str = "all"
):
    """
    Get the latest health status for each endpoint with pagination, search, and filtering.
    Returns the most recent health check for each endpoint.
    """
    try:
        # Calculate offset for pagination
        offset = (page - 1) * page_size
        
        # Get endpoints with their latest health status
        # Using a more reliable approach to get the latest health check for each endpoint
        
        # Build the base query for endpoints
        base_query = db.query(APIEndpoint).filter(
            ~APIEndpoint.url.contains("/test/health-check")
        )
        
        # Apply search filter
        if search:
            base_query = base_query.filter(
                (APIEndpoint.name.ilike(f"%{search}%")) |
                (APIEndpoint.url.ilike(f"%{search}%")) |
                (APIEndpoint.description.ilike(f"%{search}%"))
            )
        
        # Apply status filter
        if status_filter == "active":
            base_query = base_query.filter(APIEndpoint.status == True)
        elif status_filter == "inactive":
            base_query = base_query.filter(APIEndpoint.status == False)
        
        # Apply method filter
        if method_filter != "all":
            base_query = base_query.filter(APIEndpoint.method == method_filter)
        
        # Get total count of filtered endpoints
        total_endpoints = base_query.count()
        
        # Get the endpoint IDs for the current page
        endpoint_ids = base_query.order_by(APIEndpoint.name).offset(offset).limit(page_size).with_entities(APIEndpoint.endpoint_id).all()
        endpoint_id_list = [e[0] for e in endpoint_ids]
        
        logging.info(f"Querying health data for endpoint IDs: {endpoint_id_list}")
        
        if not endpoint_id_list:
            return {
                "endpoints": [],
                "total": total_endpoints,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_endpoints + page_size - 1) // page_size,
                "filters": {
                    "search": search,
                    "status_filter": status_filter,
                    "method_filter": method_filter
                }
            }
        
        # Get the latest health data for these endpoints using a subquery approach
        if endpoint_id_list:
            # Get the discovered endpoints for these API endpoints
            discovered_endpoints = db.query(DiscoveredEndpoint).join(
                APIEndpoint,
                DiscoveredEndpoint.path == APIEndpoint.url
            ).filter(
                APIEndpoint.endpoint_id.in_(endpoint_id_list)
            ).all()
            
            discovered_endpoint_ids = [de.id for de in discovered_endpoints]
            
            # Debug: Check the most recent health records in the database
            recent_health_check = db.query(
                EndpointHealth.discovered_endpoint_id,
                EndpointHealth.status,
                EndpointHealth.response_time,
                EndpointHealth.checked_at,
                EndpointHealth.status_code,
                EndpointHealth.error_message,
                EndpointHealth.failure_reason
            ).filter(
                EndpointHealth.discovered_endpoint_id.in_(discovered_endpoint_ids)
            ).order_by(EndpointHealth.checked_at.desc()).limit(5).all()
            
            # Check if the endpoints we're querying have any health records
            endpoint_health_count = db.query(
                EndpointHealth.discovered_endpoint_id,
                func.count(EndpointHealth.endpoint_health_id).label('count')
            ).filter(
                EndpointHealth.discovered_endpoint_id.in_(discovered_endpoint_ids)
            ).group_by(EndpointHealth.discovered_endpoint_id).all()
            
            # Use a more reliable approach: get all health records for these endpoints
            # and then find the latest one for each in Python
            all_health_data = db.query(
                EndpointHealth.discovered_endpoint_id,
                EndpointHealth.status,
                EndpointHealth.response_time,
                EndpointHealth.checked_at,
                EndpointHealth.status_code,
                EndpointHealth.error_message,
                EndpointHealth.failure_reason
            ).filter(
                EndpointHealth.discovered_endpoint_id.in_(discovered_endpoint_ids)
            ).order_by(
                EndpointHealth.discovered_endpoint_id,
                EndpointHealth.checked_at.desc()
            ).all()
            
            # Group by discovered_endpoint_id and get the latest record for each
            health_map = {}
            for health_record in all_health_data:
                discovered_endpoint_id = health_record[0]
                if discovered_endpoint_id not in health_map:
                    # This is the latest record for this endpoint (due to DESC ordering)
                    health_map[discovered_endpoint_id] = {
                        "status": health_record[1],
                        "response_time": health_record[2],
                        "checked_at": health_record[3],
                        "status_code": health_record[4],
                        "error_message": health_record[5],
                        "failure_reason": health_record[6]
                    }
            
            # Create a mapping from API endpoint URL to health data
            url_to_health = {}
            for de in discovered_endpoints:
                if de.id in health_map:
                    url_to_health[de.path] = health_map[de.id]
        else:
            url_to_health = {}
        
        # Get the full endpoint data
        endpoints = db.query(APIEndpoint).filter(APIEndpoint.endpoint_id.in_(endpoint_id_list)).order_by(APIEndpoint.name).all()
        
        # Format the response
        result = []
        for endpoint in endpoints:
            health_data = url_to_health.get(endpoint.url, {})
            result.append({
                "endpoint_id": endpoint.endpoint_id,
                "name": endpoint.name,
                "url": endpoint.url,
                "method": endpoint.method,
                "description": endpoint.description or "",
                "status": endpoint.status,  # Configured status
                "health_status": bool(health_data.get("status", False)),  # Ensure boolean
                "response_time": round(health_data.get("response_time", 0), 2),
                "last_checked": health_data.get("checked_at").isoformat() if health_data.get("checked_at") else None,
                "requires_auth": endpoint.requires_auth,
                "status_code": health_data.get("status_code"),
                "error_message": health_data.get("error_message"),
                "failure_reason": health_data.get("failure_reason")
            })
        
        return {
            "endpoints": result,
            "total": total_endpoints,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_endpoints + page_size - 1) // page_size,
            "filters": {
                "search": search,
                "status_filter": status_filter,
                "method_filter": method_filter
            }
        }
        
    except Exception as e:
        logging.error(f"Error fetching latest endpoint health: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch endpoint health data"
        )

# maybe buat asing.

# async def check_endpoint_health(url: str, method: str, data: dict = None):
#     """
#     Check endpoint health by:
#     1. Measuring response time (connection-only check)
#     2. Respecting the manual status setting from the API Endpoints table
    
#     With improved connection handling and database session management.
#     """
#     start_time = time.time()
#     db = None
#     endpoint_id = None
#     configured_status = None
    
#     try:
#         # First fetch the endpoint from database to check its configured status
#         db = session()
#         endpoint = db.query(APIEndpoint).filter(APIEndpoint.url == url).first()
        
#         # Get endpoint_id and configured status
#         endpoint_id = endpoint.endpoint_id if endpoint else None
#         configured_status = endpoint.status if endpoint else False
        
#         # Prepare the request
#         # Add base URL if needed
#         if not url.startswith(('http://', 'https://')):
#             base_url = os.getenv("ORIGINS", "http://127.0.0.1:8000")
#             full_url = f"{base_url}{url}"
#         else:
#             full_url = url
            
#         # Use API key for health checks instead of authentication
#         health_check_api_key = os.getenv("HEALTH_CHECK_API_KEY", "health-monitor-key")
        
#         # Include both X-API-KEY and a special health-check header to bypass JWT authentication
#         headers = {
#             "X-API-KEY": health_check_api_key,
#             "Content-Type": "application/json",
#             "X-Health-Check": "true"
#         }
        
#         # For all endpoints, do a connection-only check and measure response time
#         async with aiohttp.ClientSession() as http_session:
#             request_args = {
#                 "url": full_url,
#                 "headers": headers,
#                 "timeout": 5  # Shorter timeout to prevent hanging
#             }
            
#             # For POST/PUT/PATCH requests, add some dummy data
#             if method in ["POST", "PUT", "PATCH"]:
#                 request_args["json"] = {"health_check": True}
            
#             # Use the appropriate HTTP method
#             method_function = getattr(http_session, method.lower(), None)
#             if not method_function:
#                 raise ValueError(f"Unsupported HTTP method: {method}")
            
#             try:
#                 async with method_function(**request_args) as response:
#                     # Measure response time
#                     response_time = (time.time() - start_time) * 1000
#                     status_code = response.status
                    
#                     # Use the configured status from the database for health status
#                     # This means if status is false in the DB, the endpoint will be reported as down
#                     # regardless of connectivity
#                     status_ok = configured_status
                    
#                     logging.info(f"Health check for {url}: response_time={response_time}ms, " 
#                                 f"response_code={status_code}, configured_status={configured_status}")
                    
#                     # Create a new health entry
#                     health_entry = EndpointHealth(
#                         endpoint_id=endpoint_id,
#                         status=status_ok,  # Using configured status
#                         response_time=response_time,
#                         checked_at=datetime.now()
#                     )
#                     db.add(health_entry)
#                     db.commit()
                    
#                     return {
#                         "status": status_ok,
#                         "is_healthy": status_ok,
#                         "response_time": response_time,
#                         "status_code": status_code,
#                         "configured_status": configured_status
#                     }
                    
#             except (asyncio.TimeoutError, aiohttp.ClientError) as req_error:
#                 # Connection failure - endpoint is unreachable
#                 response_time = (time.time() - start_time) * 1000
#                 logging.error(f"Connection error for {url}: {req_error}")
                
#                 # Even if configured as up, a connection failure means the endpoint is down
#                 status_ok = False
                
#                 health_entry = EndpointHealth(
#                     endpoint_id=endpoint_id,
#                     status=status_ok,  # Using configured status
#                     response_time=response_time,
#                     checked_at=datetime.now(),
#                 )
#                 db.add(health_entry)
#                 db.commit()
                
#                 return {
#                     "status": status_ok,
#                     "is_healthy": False,
#                     "response_time": response_time,
#                     "error": str(req_error)
#                 }
                
#     except Exception as e:
#         # Handle other exceptions
#         logging.error(f"Health check failed for {url}: {e}")
#         response_time = (time.time() - start_time) * 1000 if 'start_time' in locals() else None
        
#         # Try to record the health check error
#         try:
#             if db is None or not db.is_active:
#                 db = session()
                
#             health_entry = EndpointHealth(
#                 endpoint_id=endpoint_id,
#                 endpoint_url=url,
#                 status=False,
#                 status_code=0,
#                 response_time=response_time,
#                 is_healthy=False,
#                 checked_at=datetime.now(),
#                 error_message=str(e)
#             )
#             db.add(health_entry)
#             db.commit()
#         except Exception as inner_e:
#             logging.error(f"Failed to store failed health check: {inner_e}")
#             if db and db.is_active:
#                 db.rollback()
        
#         return {
#             "status": False,
#             "is_healthy": False,
#             "response_time": response_time,
#             "error": str(e)
#         }
#     finally:
#         # Always close the database session if it was created
#         if db:
#             try:
#                 db.close()
#             except Exception as close_error:
#                 logging.error(f"Error closing database connection: {close_error}")
    
@router.get("/overview-metrics")
def overview_metrics(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    total_requests = db.query(func.count(APIRequest.api_req_id)).scalar()
    failed_requests = db.query(func.count()).filter(APIRequest.status_code >= 400).scalar()
    total_4xx = db.query(func.count()).filter(APIRequest.status_code.between(400, 499)).scalar()
    total_5xx = db.query(func.count()).filter(APIRequest.status_code >= 500).scalar()
    avg_response_time = db.query(func.avg(APIRequest.response_time)).scalar()

    return {
        "total_requests": total_requests,
        "failed_requests": failed_requests,
        "total_4xx": total_4xx,
        "total_5xx": total_5xx,
        "avg_response_time": round(avg_response_time, 3) if avg_response_time else 0
    }

@router.get("/requests-breakdown")
def requests_breakdown(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    requests_by_method = db.query(
        APIRequest.method, func.count(APIRequest.api_req_id).label("count")
    ).group_by(APIRequest.method).all()

    requests_by_status = db.query(
        APIRequest.status_code, func.count(APIRequest.api_req_id).label("count")
    ).group_by(APIRequest.status_code).all()

    return {
        "requests_by_method": {method: count for method, count in requests_by_method},
        "requests_by_status": {code: count for code, count in requests_by_status}
    }

@router.get("/failures-breakdown")
def failures_breakdown(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    failures_by_method = db.query(
        APIRequest.method, func.count(APIRequest.api_req_id)
    ).filter(APIRequest.status_code >= 400).group_by(APIRequest.method).all()

    failures_by_status = db.query(
        APIRequest.status_code, func.count(APIRequest.api_req_id)
    ).filter(APIRequest.status_code >= 400).group_by(APIRequest.status_code).all()

    return {
        "failures_by_method": {method: count for method, count in failures_by_method},
        "failures_by_status": {code: count for code, count in failures_by_status}
    }

@router.get("/performance-trends")
def performance_trends(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    performance_by_time = db.query(
        func.date_trunc("hour", APIRequest.timestamp).label("hour"),
        func.avg(APIRequest.response_time).label("avg_response_time")
    ).group_by("hour").order_by("hour").all()

    slow_requests = db.query(
        APIRequest.endpoint, func.avg(APIRequest.response_time)
    ).group_by(APIRequest.endpoint).order_by(func.avg(APIRequest.response_time).desc()).limit(5).all()

    return {
        "performance_trends": [{"hour": str(hour), "avg_response_time": round(rt, 3)} for hour, rt in performance_by_time],
        "slow_requests": [{"endpoint": ep, "avg_response_time": round(rt, 3)} for ep, rt in slow_requests]
    }


@router.get("/client-insights")
def client_insights(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    requests_by_client = db.query(
        APIRequest.client_ip, func.count(APIRequest.api_req_id).label("count")
    ).group_by(APIRequest.client_ip).order_by(func.count().desc()).limit(10).all()

    return {
        "requests_by_client": [{"client_ip": ip, "count": count} for ip, count in requests_by_client]
    }

@router.get("/activity")
def get_activity_data(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency,
    page: int = 1,
    page_size: int = 10
):
    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    total = db.query(func.count(ActivityLog.log_id)).scalar()

    # Get paginated activities with user information
    activities = db.query(
        ActivityLog,
        Users.user_name,
        Users.user_email
    ).join(
        Users,
        ActivityLog.user_id == Users.user_id,
        isouter=True  # Use outer join to include activities without user info
    ).order_by(
        ActivityLog.timestamp.desc()
    ).offset(
        offset
    ).limit(
        page_size
    ).all()
    
    return {
        "activities": [
            {
                "log_id": activity.ActivityLog.log_id,
                "activity_type": "user",
                "detail": activity.ActivityLog.action,
                "timestamp": activity.ActivityLog.timestamp.isoformat(),
                "client_ip": activity.ActivityLog.client_ip,
                "user_name": activity.user_name or "Unknown",
                "user_email": activity.user_email or "Unknown",
                "status": "success"  # Default to success for user activities
            }
            for activity in activities
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.post("/run-health-scan")
async def run_health_scan(
    scan_data: dict,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency
):
    try:
        # Extract scan period from request data
        scan_period = scan_data.get("scan_period", "1_week")
        
        # Initialize health checker
        from enhanced_health_check import health_checker
        await health_checker.initialize()
        
        # Get all endpoints
        endpoints = db.query(APIEndpoint).all()
        
        if not endpoints:
            return {
                "status": "warning",
                "message": "No endpoints found to scan",
                "results": []
            }
        
        # Run health checks
        results = await health_checker.check_all_main_endpoints(batch_size=5)
        
        # Clean up test data
        from cleanup_test_data import cleanup_test_data
        cleanup_test_data()
        
        # Calculate summary statistics
        total_endpoints = len(results)
        healthy_endpoints = sum(1 for r in results if r.get("status", False))
        unhealthy_endpoints = total_endpoints - healthy_endpoints
        
        return {
            "status": "success",
            "message": f"Health scan completed for period: {scan_period}",
            "summary": {
                "total_endpoints": total_endpoints,
                "healthy_endpoints": healthy_endpoints,
                "unhealthy_endpoints": unhealthy_endpoints,
                "scan_period": scan_period
            },
            "results": results
        }
    except Exception as e:
        logging.error(f"Error running health scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_analytics_summary(
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency,
    time_range: str = "24h"
):
    """Get analytics summary."""
    try:
        # Get total requests
        total_requests = db.query(func.count(APIRequest.api_req_id)).scalar() or 0
        
        # Get success rate
        success_count = db.query(func.count(APIRequest.api_req_id)).filter(
            APIRequest.status_code.between(200, 299)
        ).scalar() or 0
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        # Get average response time
        avg_response_time = db.query(func.avg(APIRequest.response_time)).scalar() or 0
        
        # Get active endpoints
        active_endpoints = db.query(func.count(APIEndpoint.endpoint_id)).filter(
            APIEndpoint.status == True
        ).scalar() or 0
        
        # Get total endpoints
        total_endpoints = db.query(func.count(APIEndpoint.endpoint_id)).scalar() or 0
        
        # Calculate health metrics
        health_status = db.query(
            func.avg(case((EndpointHealth.status == True, 100), else_=0)).label('uptime'),
            func.avg(EndpointHealth.response_time).label('avg_response_time')
        ).first()
        
        uptime = float(health_status[0]) if health_status and health_status[0] is not None else 0
        health_response_time = float(health_status[1]) if health_status and health_status[1] is not None else 0
        
        return {
            "summary": {
                "total_requests": total_requests,
                "success_rate": round(success_rate, 2),
                "average_response_time": round(float(avg_response_time), 2),
                "error_rate": round(100 - success_rate, 2),
                "active_endpoints": active_endpoints,
                "total_endpoints": total_endpoints,
                "average_uptime": round(uptime, 2),
                "average_error_rate": round(100 - uptime, 2),
                "health_check_response_time": round(health_response_time, 2)
            },
            "time_range": time_range,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating analytics summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate analytics summary: {str(e)}"
        )

@router.get("/remote-servers/{server_id}/analytics")
async def get_remote_server_analytics(
    server_id: int,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency
):
    try:
        # Get all discovered endpoints for this remote server
        endpoints = db.query(DiscoveredEndpoint).filter(DiscoveredEndpoint.remote_server_id == server_id).all()

        endpoint_data = []
        healthy_count = 0
        unhealthy_count = 0
        response_times = []

        for endpoint in endpoints:
            # Get the latest health record for this endpoint
            latest_health = (
                db.query(EndpointHealth)
                .filter(EndpointHealth.discovered_endpoint_id == endpoint.id)
                .order_by(EndpointHealth.checked_at.desc())
                .first()
            )
            if latest_health:
                is_healthy = bool(latest_health.is_healthy)
                if is_healthy:
                    healthy_count += 1
                else:
                    unhealthy_count += 1
                response_time = latest_health.response_time or 0
                response_times.append(response_time)
                endpoint_data.append({
                    "id": endpoint.id,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "status": latest_health.status,
                    "is_healthy": is_healthy,
                    "last_checked": latest_health.checked_at.isoformat() if latest_health.checked_at else None,
                    "response_time": response_time,
                    "status_code": latest_health.status_code,
                    "error_message": latest_health.error_message,
                    "failure_reason": latest_health.failure_reason
                })
            else:
                unhealthy_count += 1
                endpoint_data.append({
                    "id": endpoint.id,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "status": None,
                    "is_healthy": False,
                    "last_checked": None,
                    "response_time": 0,
                    "status_code": None,
                    "error_message": None,
                    "failure_reason": None
                })

        total_endpoints = len(endpoints)
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "metrics": {
                "total_endpoints": total_endpoints,
                "healthy_endpoints": healthy_count,
                "unhealthy_endpoints": unhealthy_count,
                "average_response_time": float(avg_response_time)
            },
            "endpoints": endpoint_data
        }
    except Exception as e:
        logger.error(f"Error getting remote server analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remote-servers/{server_id}/run-health-scan")
async def run_remote_server_health_scan_api(
    server_id: int,
    background_tasks: BackgroundTasks,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = Depends(get_db),
    frequency: str = "1d"
):
    try:
        # Convert frequency to seconds
        frequency_seconds = {
            "1d": 24 * 60 * 60,  # 1 day
            "1w": 7 * 24 * 60 * 60,  # 1 week
            "1m": 30 * 24 * 60 * 60,  # 1 month (approximate)
        }.get(frequency, 24 * 60 * 60)  # Default to 1 day if invalid frequency

        # Run initial scan
        background_tasks.add_task(asyncio.run, run_remote_server_health_scan(server_id))

        # Schedule recurring scans
        async def schedule_scans():
            while True:
                await asyncio.sleep(frequency_seconds)
                await run_remote_server_health_scan(server_id)

        background_tasks.add_task(schedule_scans)

        return {
            "message": f"Health scan for remote server {server_id} started with frequency {frequency}",
            "frequency": frequency,
            "next_scan_in": frequency_seconds
        }
    except Exception as e:
        logger.error(f"Error scheduling health scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/remote-servers/{server_id}/performance-analytics")
async def get_remote_server_performance_analytics(
    server_id: int,
    api_key: Annotated[str, Depends(api_key_header)],
    user: user_dependency,
    db: Session = db_dependency,
    time_range: str = "7d"
):
    """Get comprehensive performance analytics for a remote server."""
    try:
        from datetime import datetime, timedelta
        
        # Calculate time range
        now = datetime.now()
        if time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=7)  # Default to 7 days
        
        # Get all health records for this remote server's endpoints
        health_records = db.query(
            EndpointHealth,
            DiscoveredEndpoint
        ).join(
            DiscoveredEndpoint,
            EndpointHealth.discovered_endpoint_id == DiscoveredEndpoint.id
        ).filter(
            DiscoveredEndpoint.remote_server_id == server_id,
            EndpointHealth.checked_at >= start_time
        ).order_by(
            EndpointHealth.checked_at.desc()
        ).all()
        
        if not health_records:
            return {
                "message": "No performance data available for the specified time range",
                "time_range": time_range,
                "data": {
                    "average_response_time_by_day": [],
                    "average_response_time_by_hour": [],
                    "slowest_endpoints": [],
                    "response_time_by_method": {},
                    "traffic_correlation": []
                }
            }
        
        # 1. Average Response Time by Day
        daily_response_times = {}
        hourly_response_times = {}
        
        for health, endpoint in health_records:
            if health.response_time is not None:
                # Daily aggregation
                day_key = health.checked_at.strftime("%Y-%m-%d")
                if day_key not in daily_response_times:
                    daily_response_times[day_key] = []
                daily_response_times[day_key].append(health.response_time)
                
                # Hourly aggregation
                hour_key = health.checked_at.strftime("%Y-%m-%d %H:00")
                if hour_key not in hourly_response_times:
                    hourly_response_times[hour_key] = []
                hourly_response_times[hour_key].append(health.response_time)
        
        # Calculate averages
        avg_response_time_by_day = [
            {
                "date": day,
                "average_response_time": sum(times) / len(times),
                "count": len(times)
            }
            for day, times in sorted(daily_response_times.items())
        ]
        
        avg_response_time_by_hour = [
            {
                "hour": hour,
                "average_response_time": sum(times) / len(times),
                "count": len(times)
            }
            for hour, times in sorted(hourly_response_times.items())
        ]
        
        # 2. Slowest Endpoints (Top 5)
        endpoint_performance = {}
        for health, endpoint in health_records:
            if health.response_time is not None:
                endpoint_key = f"{endpoint.method} {endpoint.path}"
                if endpoint_key not in endpoint_performance:
                    endpoint_performance[endpoint_key] = {
                        "method": endpoint.method,
                        "path": endpoint.path,
                        "response_times": [],
                        "total_checks": 0,
                        "successful_checks": 0
                    }
                endpoint_performance[endpoint_key]["response_times"].append(health.response_time)
                endpoint_performance[endpoint_key]["total_checks"] += 1
                if health.is_healthy:
                    endpoint_performance[endpoint_key]["successful_checks"] += 1
        
        # Calculate average response times and sort by slowest
        slowest_endpoints = []
        for endpoint_key, data in endpoint_performance.items():
            if data["response_times"]:
                avg_response_time = sum(data["response_times"]) / len(data["response_times"])
                success_rate = (data["successful_checks"] / data["total_checks"]) * 100 if data["total_checks"] > 0 else 0
                slowest_endpoints.append({
                    "endpoint": endpoint_key,
                    "method": data["method"],
                    "path": data["path"],
                    "average_response_time": avg_response_time,
                    "total_checks": data["total_checks"],
                    "success_rate": success_rate
                })
        
        # Sort by average response time (slowest first) and take top 5
        slowest_endpoints.sort(key=lambda x: x["average_response_time"], reverse=True)
        slowest_endpoints = slowest_endpoints[:5]
        
        # 3. Response Time Comparison by HTTP Method
        method_performance = {}
        for health, endpoint in health_records:
            if health.response_time is not None:
                method = endpoint.method
                if method not in method_performance:
                    method_performance[method] = {
                        "response_times": [],
                        "total_checks": 0,
                        "successful_checks": 0
                    }
                method_performance[method]["response_times"].append(health.response_time)
                method_performance[method]["total_checks"] += 1
                if health.is_healthy:
                    method_performance[method]["successful_checks"] += 1
        
        response_time_by_method = {}
        for method, data in method_performance.items():
            if data["response_times"]:
                avg_response_time = sum(data["response_times"]) / len(data["response_times"])
                success_rate = (data["successful_checks"] / data["total_checks"]) * 100 if data["total_checks"] > 0 else 0
                response_time_by_method[method] = {
                    "average_response_time": avg_response_time,
                    "total_checks": data["total_checks"],
                    "success_rate": success_rate,
                    "min_response_time": min(data["response_times"]),
                    "max_response_time": max(data["response_times"])
                }
        
        # 4. Correlation between high traffic and slow responses
        # Group by hour and calculate traffic volume vs average response time
        hourly_traffic_correlation = {}
        for health, endpoint in health_records:
            hour_key = health.checked_at.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_traffic_correlation:
                hourly_traffic_correlation[hour_key] = {
                    "checks": 0,
                    "response_times": [],
                    "timestamp": health.checked_at
                }
            hourly_traffic_correlation[hour_key]["checks"] += 1
            if health.response_time is not None:
                hourly_traffic_correlation[hour_key]["response_times"].append(health.response_time)
        
        traffic_correlation = []
        for hour, data in sorted(hourly_traffic_correlation.items()):
            if data["response_times"]:
                avg_response_time = sum(data["response_times"]) / len(data["response_times"])
                traffic_correlation.append({
                    "hour": hour,
                    "traffic_volume": data["checks"],
                    "average_response_time": avg_response_time,
                    "timestamp": data["timestamp"].isoformat()
                })
        
        # 5. Traffic Trends Over Time
        # Group by day and hour for traffic volume analysis
        daily_traffic = {}
        hourly_traffic = {}
        
        for health, endpoint in health_records:
            # Daily traffic
            day_key = health.checked_at.strftime("%Y-%m-%d")
            if day_key not in daily_traffic:
                daily_traffic[day_key] = {
                    "total_checks": 0,
                    "successful_checks": 0,
                    "failed_checks": 0,
                    "avg_response_time": 0,
                    "response_times": []
                }
            daily_traffic[day_key]["total_checks"] += 1
            if health.is_healthy:
                daily_traffic[day_key]["successful_checks"] += 1
            else:
                daily_traffic[day_key]["failed_checks"] += 1
            if health.response_time is not None:
                daily_traffic[day_key]["response_times"].append(health.response_time)
            
            # Hourly traffic
            hour_key = health.checked_at.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_traffic:
                hourly_traffic[hour_key] = {
                    "total_checks": 0,
                    "successful_checks": 0,
                    "failed_checks": 0,
                    "avg_response_time": 0,
                    "response_times": [],
                    "timestamp": health.checked_at
                }
            hourly_traffic[hour_key]["total_checks"] += 1
            if health.is_healthy:
                hourly_traffic[hour_key]["successful_checks"] += 1
            else:
                hourly_traffic[hour_key]["failed_checks"] += 1
            if health.response_time is not None:
                hourly_traffic[hour_key]["response_times"].append(health.response_time)
        
        # Calculate averages and prepare traffic trends data
        daily_traffic_trends = []
        for day, data in sorted(daily_traffic.items()):
            avg_response_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0
            success_rate = (data["successful_checks"] / data["total_checks"]) * 100 if data["total_checks"] > 0 else 0
            daily_traffic_trends.append({
                "date": day,
                "total_checks": data["total_checks"],
                "successful_checks": data["successful_checks"],
                "failed_checks": data["failed_checks"],
                "success_rate": success_rate,
                "avg_response_time": avg_response_time
            })
        
        hourly_traffic_trends = []
        for hour, data in sorted(hourly_traffic.items()):
            avg_response_time = sum(data["response_times"]) / len(data["response_times"]) if data["response_times"] else 0
            success_rate = (data["successful_checks"] / data["total_checks"]) * 100 if data["total_checks"] > 0 else 0
            hourly_traffic_trends.append({
                "hour": hour,
                "total_checks": data["total_checks"],
                "successful_checks": data["successful_checks"],
                "failed_checks": data["failed_checks"],
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "timestamp": data["timestamp"].isoformat()
            })
        
        # Calculate traffic spikes and dips
        def detect_anomalies(traffic_data, threshold=2.0):
            """Detect traffic spikes and dips using statistical analysis"""
            if len(traffic_data) < 3:
                return []
            
            volumes = [item["total_checks"] for item in traffic_data]
            mean_volume = sum(volumes) / len(volumes)
            std_volume = (sum((v - mean_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5
            
            anomalies = []
            for i, item in enumerate(traffic_data):
                volume = item["total_checks"]
                z_score = abs(volume - mean_volume) / std_volume if std_volume > 0 else 0
                
                if z_score > threshold:
                    anomaly_type = "spike" if volume > mean_volume else "dip"
                    anomalies.append({
                        "index": i,
                        "type": anomaly_type,
                        "timestamp": item.get("timestamp", item.get("date", "")),
                        "volume": volume,
                        "z_score": z_score,
                        "severity": "high" if z_score > 3.0 else "medium" if z_score > 2.5 else "low"
                    })
            
            return anomalies
        
        daily_anomalies = detect_anomalies(daily_traffic_trends)
        hourly_anomalies = detect_anomalies(hourly_traffic_trends)
        
        # Calculate correlation coefficient
        if len(traffic_correlation) > 1:
            traffic_volumes = [item["traffic_volume"] for item in traffic_correlation]
            response_times = [item["average_response_time"] for item in traffic_correlation]
            
            # Simple correlation calculation
            mean_traffic = sum(traffic_volumes) / len(traffic_volumes)
            mean_response = sum(response_times) / len(response_times)
            
            numerator = sum((t - mean_traffic) * (r - mean_response) for t, r in zip(traffic_volumes, response_times))
            denominator_traffic = sum((t - mean_traffic) ** 2 for t in traffic_volumes)
            denominator_response = sum((r - mean_response) ** 2 for r in response_times)
            
            if denominator_traffic > 0 and denominator_response > 0:
                correlation_coefficient = numerator / (denominator_traffic * denominator_response) ** 0.5
            else:
                correlation_coefficient = 0
        else:
            correlation_coefficient = 0
        
        return {
            "time_range": time_range,
            "data": {
                "average_response_time_by_day": avg_response_time_by_day,
                "average_response_time_by_hour": avg_response_time_by_hour,
                "slowest_endpoints": slowest_endpoints,
                "response_time_by_method": response_time_by_method,
                "traffic_correlation": {
                    "data": traffic_correlation,
                    "correlation_coefficient": correlation_coefficient,
                    "interpretation": "Negative correlation means higher traffic leads to faster responses (good scaling). Positive correlation means higher traffic leads to slower responses (potential bottleneck)."
                },
                "traffic_trends": {
                    "daily": daily_traffic_trends,
                    "hourly": hourly_traffic_trends,
                    "anomalies": {
                        "daily": daily_anomalies,
                        "hourly": hourly_anomalies
                    }
                }
            },
            "summary": {
                "total_health_checks": len(health_records),
                "time_period_start": start_time.isoformat(),
                "time_period_end": now.isoformat(),
                "overall_average_response_time": sum(record[0].response_time or 0 for record in health_records) / len([r for r in health_records if r[0].response_time is not None]) if any(r[0].response_time is not None for r in health_records) else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting remote server performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))