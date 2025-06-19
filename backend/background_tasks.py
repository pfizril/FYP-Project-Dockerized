import asyncio
import logging
from sqlalchemy.orm import Session
from models import RemoteServer
from remote_server_service import RemoteServerService
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

logger = logging.getLogger(__name__)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def monitor_remote_servers():
    """Background task to monitor all remote servers"""
    while True:
        try:
            # Create new database session
            db = SessionLocal()
            service = RemoteServerService(db)
            
            # Get all active servers
            servers = db.query(RemoteServer).filter(RemoteServer.is_active == True).all()
            
            for server in servers:
                try:
                    logger.info(f"Starting discovery and monitoring for server: {server.name}")
                    result = await service.discover_and_monitor(server.id)
                    logger.info(f"Completed discovery and monitoring for server {server.name}: {result}")
                except Exception as e:
                    logger.error(f"Error monitoring server {server.name}: {str(e)}")
                    
            db.close()
        except Exception as e:
            logger.error(f"Error in monitor_remote_servers: {str(e)}")
            
        # Wait for 5 minutes before next check
        await asyncio.sleep(300)

def start_background_tasks():
    """Start all background tasks"""
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_remote_servers())
    logger.info("Started background monitoring tasks") 