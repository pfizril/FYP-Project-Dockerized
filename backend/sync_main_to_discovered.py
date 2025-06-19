#!/usr/bin/env python
"""
Sync main endpoints from api_endpoints into discovered_endpoints if not already present.
"""
from models import APIEndpoint, DiscoveredEndpoint, RemoteServer
from database import get_db_session
from datetime import datetime
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_endpoint_hash(path, method):
    return hashlib.sha256(f"{path}:{method}".encode("utf-8")).hexdigest()

def sync_main_to_discovered():
    with get_db_session() as db:
        # Ensure remote_server_id=-1 exists
        main_server = db.query(RemoteServer).filter_by(id=-1).first()
        if not main_server:
            main_server = RemoteServer(
                id=-1,
                name='Main System',
                base_url='http://localhost',
                created_by=1,  # Change to a valid user_id if needed
                is_active=True
            )
            db.add(main_server)
            db.commit()
            logger.info("Inserted 'Main System' into remote_servers with id=-1.")
        main_endpoints = db.query(APIEndpoint).all()
        count_added = 0
        for ep in main_endpoints:
            exists = db.query(DiscoveredEndpoint).filter_by(path=ep.url, method=ep.method).first()
            if not exists:
                discovered = DiscoveredEndpoint(
                    remote_server_id=-1,  # Use -1 to indicate main/local endpoints
                    path=ep.url,
                    method=ep.method,
                    description=ep.description,
                    parameters=None,
                    response_schema=None,
                    discovered_at=datetime.now(),
                    last_checked=None,
                    is_active=ep.status,
                    endpoint_hash=generate_endpoint_hash(ep.url, ep.method)
                )
                db.add(discovered)
                count_added += 1
        db.commit()
        logger.info(f"Sync complete. Added {count_added} main endpoints to discovered_endpoints.")

if __name__ == "__main__":
    sync_main_to_discovered() 