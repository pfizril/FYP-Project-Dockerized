from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session, user: Optional[Dict] = None):
        self.db = db
        self.user = user
        logger.info(f"AnalyticsService initialized with user: {user}")

    async def collect_server_metrics(self, server_id: int) -> Dict:
        """Collect metrics for a specific remote server."""
        try:
            # Get server details
            server = self.db.execute(
                text("SELECT * FROM remote_servers WHERE id = :server_id"),
                {"server_id": server_id}
            ).fetchone()

            if not server:
                raise ValueError(f"Server with ID {server_id} not found")

            # Calculate uptime and response time metrics
            metrics = {
                "server_id": server_id,
                "name": server.name,
                "status": server.status,
                "last_checked": server.last_checked,
                "retry_count": server.retry_count,
                "uptime_percentage": self._calculate_uptime(server_id),
                "average_response_time": self._calculate_response_time(server_id),
                "error_rate": self._calculate_error_rate(server_id),
                "last_error": server.last_error
            }

            # Store metrics in analytics table
            self._store_metrics(metrics)
            
            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics for server {server_id}: {str(e)}")
            raise

    def _calculate_uptime(self, server_id: int) -> float:
        """Calculate server uptime percentage for the last 24 hours."""
        try:
            # Get status checks for the last 24 hours
            result = self.db.execute(
                text("""
                    SELECT status, COUNT(*) as count
                    FROM server_status_checks
                    WHERE server_id = :server_id
                    AND check_time >= NOW() - INTERVAL '24 hours'
                    GROUP BY status
                """),
                {"server_id": server_id}
            ).fetchall()

            total_checks = sum(row.count for row in result)
            if total_checks == 0:
                return 0.0

            active_checks = sum(row.count for row in result if row.status == 'active')
            return (active_checks / total_checks) * 100

        except Exception as e:
            logger.error(f"Error calculating uptime: {str(e)}")
            return 0.0

    def _calculate_response_time(self, server_id: int) -> float:
        """Calculate average response time for the last hour."""
        try:
            result = self.db.execute(
                text("""
                    SELECT AVG(response_time) as avg_time
                    FROM server_status_checks
                    WHERE server_id = :server_id
                    AND check_time >= NOW() - INTERVAL '1 hour'
                """),
                {"server_id": server_id}
            ).fetchone()

            return float(result.avg_time) if result.avg_time else 0.0

        except Exception as e:
            logger.error(f"Error calculating response time: {str(e)}")
            return 0.0

    def _calculate_error_rate(self, server_id: int) -> float:
        """Calculate error rate for the last 24 hours."""
        try:
            result = self.db.execute(
                text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'error') as error_count,
                        COUNT(*) as total_count
                    FROM server_status_checks
                    WHERE server_id = :server_id
                    AND check_time >= NOW() - INTERVAL '24 hours'
                """),
                {"server_id": server_id}
            ).fetchone()

            if result.total_count == 0:
                return 0.0

            return (result.error_count / result.total_count) * 100

        except Exception as e:
            logger.error(f"Error calculating error rate: {str(e)}")
            return 0.0

    def _store_metrics(self, metrics: Dict) -> None:
        """Store collected metrics in the analytics table."""
        try:
            self.db.execute(
                text("""
                    INSERT INTO server_analytics (
                        server_id,
                        metrics_data,
                        collected_at
                    ) VALUES (
                        :server_id,
                        :metrics_data,
                        NOW()
                    )
                """),
                {
                    "server_id": metrics["server_id"],
                    "metrics_data": json.dumps(metrics)
                }
            )
            self.db.commit()

        except Exception as e:
            logger.error(f"Error storing metrics: {str(e)}")
            self.db.rollback()
            raise

    async def get_server_analytics(self, server_id: int, time_range: str = "24h", user: Optional[Dict] = None) -> Dict:
        """Get analytics data for a specific server."""
        try:
            # Ensure we have a user
            if not user and not self.user:
                raise ValueError("User information is required")
            
            # Use the provided user or fall back to instance user
            analytics_user = user or self.user

            # Convert time range to interval
            interval_map = {
                "1h": "1 hour",
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days"
            }
            interval = interval_map.get(time_range, "24 hours")

            # Get analytics data
            result = self.db.execute(
                text("""
                    SELECT metrics_data
                    FROM server_analytics
                    WHERE server_id = :server_id
                    AND collected_at >= NOW() - INTERVAL :interval
                    ORDER BY collected_at DESC
                """),
                {
                    "server_id": server_id,
                    "interval": interval
                }
            ).fetchall()

            # Process and aggregate metrics
            metrics = [json.loads(row.metrics_data) for row in result]
            
            # Calculate summary metrics
            total_requests = sum(m.get("total_requests", 0) for m in metrics)
            failed_requests = sum(m.get("failed_requests", 0) for m in metrics)
            client_errors = sum(m.get("failure_breakdown", {}).get("client_error", 0) for m in metrics)
            server_errors = sum(m.get("failure_breakdown", {}).get("server_error", 0) for m in metrics)
            avg_response_time = sum(m.get("average_response_time", 0) for m in metrics) / len(metrics) if metrics else 0
            
            logger.info(f"Calculated metrics for server {server_id}: total_requests={total_requests}, failed_requests={failed_requests}")
            
            return {
                "metrics": {
                    "total_requests": total_requests,
                    "failed_requests": failed_requests,
                    "failure_breakdown": {
                        "client_error": client_errors,
                        "server_error": server_errors
                    },
                    "average_response_time": avg_response_time
                }
            }

        except Exception as e:
            logger.error(f"Error getting analytics for server {server_id}: {str(e)}")
            return {
                "metrics": {
                    "total_requests": 0,
                    "failed_requests": 0,
                    "failure_breakdown": {
                        "client_error": 0,
                        "server_error": 0
                    },
                    "average_response_time": 0
                }
            }

    def _generate_summary(self, metrics: List[Dict]) -> Dict:
        """Generate summary statistics from metrics data."""
        if not metrics:
            return {}

        return {
            "average_uptime": sum(m["uptime_percentage"] for m in metrics) / len(metrics),
            "average_response_time": sum(m["average_response_time"] for m in metrics) / len(metrics),
            "average_error_rate": sum(m["error_rate"] for m in metrics) / len(metrics),
            "total_checks": len(metrics),
            "last_status": metrics[0]["status"] if metrics else None
        }

    def get_remote_server_analytics(self, server_id: int) -> dict:
        """Get analytics data for a remote server"""
        with get_db_session() as db:
            # Get all discovered endpoints for this server
            endpoints = db.query(DiscoveredEndpoint).filter(
                DiscoveredEndpoint.remote_server_id == server_id,
                DiscoveredEndpoint.is_active == True
            ).all()
            
            # Get latest health check for each endpoint
            total_response_time = 0
            healthy_count = 0
            
            endpoint_data = []
            for endpoint in endpoints:
                # Get latest health check
                latest_health = db.query(EndpointHealth).filter(
                    EndpointHealth.discovered_endpoint_id == endpoint.id
                ).order_by(EndpointHealth.checked_at.desc()).first()
                
                if latest_health:
                    total_response_time += latest_health.response_time
                    if latest_health.is_healthy:
                        healthy_count += 1
                
                endpoint_data.append({
                    "id": endpoint.id,
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "status": "active",
                    "last_checked": latest_health.checked_at.isoformat() if latest_health else None,
                    "response_time": latest_health.response_time if latest_health else 0,
                    "status_code": latest_health.status_code if latest_health else None
                })
            
            # Get health history
            health_history = db.query(EndpointHealth).join(
                DiscoveredEndpoint,
                EndpointHealth.discovered_endpoint_id == DiscoveredEndpoint.id
            ).filter(
                DiscoveredEndpoint.remote_server_id == server_id
            ).order_by(
                EndpointHealth.checked_at.desc()
            ).limit(100).all()
            
            health_history_data = [
                {
                    "id": health.id,
                    "discovered_endpoint_id": health.discovered_endpoint_id,
                    "status": health.status,
                    "is_healthy": health.is_healthy,
                    "response_time": health.response_time,
                    "checked_at": health.checked_at.isoformat(),
                    "status_code": health.status_code,
                    "error_message": health.error_message,
                    "failure_reason": health.failure_reason
                }
                for health in health_history
            ]
            
            total_endpoints = len(endpoints)
            unhealthy_count = total_endpoints - healthy_count
            avg_response_time = total_response_time / total_endpoints if total_endpoints > 0 else 0
            
            return {
                "metrics": {
                    "total_endpoints": total_endpoints,
                    "healthy_endpoints": healthy_count,
                    "unhealthy_endpoints": unhealthy_count,
                    "average_response_time": avg_response_time
                },
                "endpoints": endpoint_data,
                "health_history": health_history_data
            } 