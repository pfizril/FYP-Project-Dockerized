from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import logging
from contextlib import contextmanager
import time
from typing import Generator
import threading
from queue import Queue
import atexit
from concurrent.futures import ThreadPoolExecutor

# Configure logging for database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connection pool settings
POOL_SIZE = 50  # Increased for dashboard concurrent requests
MAX_OVERFLOW = 50
POOL_TIMEOUT = 30
POOL_RECYCLE = 300
POOL_MAX_OVERFLOW = 30

# Create a custom pool class that implements connection recycling
class CustomQueuePool(QueuePool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recycle_connections = True
        self._last_recycle = time.time()
        self._recycle_lock = threading.Lock()
        self._connection_count = 0
        self._connection_lock = threading.Lock()

    def _do_get(self):
        with self._recycle_lock:
            # Check if we need to recycle connections
            if self._recycle_connections and (time.time() - self._last_recycle) > POOL_RECYCLE:
                self._recycle_connections = False
                self._last_recycle = time.time()
                # Only recycle if we have connections and no active connections
                if self.size() > 0 and self._connection_count == 0:
                    logger.info("Recycling connections in pool")
                    self.dispose()
        
        with self._connection_lock:
            self._connection_count += 1
        return super()._do_get()

    def _do_return(self, conn):
        with self._connection_lock:
            self._connection_count -= 1
        return super()._do_return(conn)

# Create engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    poolclass=CustomQueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=POOL_RECYCLE,
    echo_pool=True,
    pool_use_lifo=True,
    pool_reset_on_return='rollback',
    max_identifier_length=63
)

# Session management
class SessionManager:
    def __init__(self):
        self._session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )
        self._session_queue = Queue(maxsize=POOL_SIZE + MAX_OVERFLOW)
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=POOL_SIZE)
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the session pool with pre-created sessions"""
        try:
            for _ in range(POOL_SIZE):
                session = self._session_factory()
                self._session_queue.put(session)
            logger.info(f"Initialized session pool with {POOL_SIZE} sessions")
        except Exception as e:
            logger.error(f"Error initializing session pool: {e}")

    def get_session(self):
        """Get a session from the pool"""
        try:
            with self._lock:
                if self._session_queue.empty():
                    logger.info("Session pool empty, creating new session")
                    return self._session_factory()
                try:
                    session = self._session_queue.get(timeout=POOL_TIMEOUT)
                    return session
                except Exception as e:
                    logger.warning(f"Timeout getting session from pool: {e}")
                    return self._session_factory()
        except Exception as e:
            logger.error(f"Failed to get session from pool: {e}")
            return self._session_factory()

    def return_session(self, session):
        """Return a session to the pool"""
        try:
            with self._lock:
                if not self._session_queue.full():
                    self._session_queue.put(session)
                else:
                    logger.info("Session pool full, closing session")
                    session.close()
        except Exception as e:
            logger.error(f"Error returning session to pool: {e}")
            try:
                session.close()
            except:
                pass

    def cleanup(self):
        """Cleanup all sessions in the pool"""
        with self._lock:
            while not self._session_queue.empty():
                try:
                    session = self._session_queue.get_nowait()
                    session.close()
                except Exception as e:
                    logger.error(f"Error cleaning up session: {e}")
        self._executor.shutdown(wait=True)

# Create session manager instance
session_manager = SessionManager()

# Register cleanup on exit
atexit.register(session_manager.cleanup)

# Event listeners for connection pool management
@event.listens_for(engine, 'checkout')
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log when a connection is checked out from the pool"""
    logger.debug(f"Connection checked out from pool. Pool size: {engine.pool.size()}")

@event.listens_for(engine, 'checkin')
def receive_checkin(dbapi_connection, connection_record):
    """Log when a connection is checked in to the pool"""
    logger.debug(f"Connection checked in to pool. Pool size: {engine.pool.size()}")

@event.listens_for(engine, 'connect')
def receive_connect(dbapi_connection, connection_record):
    """Log when a new connection is created"""
    logger.debug("New database connection created")

# FastAPI dependency
def get_db() -> Generator:
    """Dependency for FastAPI endpoints that provides a database session"""
    session = session_manager.get_session()
    try:
        yield session
    finally:
        session_manager.return_session(session)

@contextmanager
def get_db_session():
    """Context manager for database sessions with retry logic"""
    session = None
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            session = session_manager.get_session()
            yield session
            session.commit()  # Commit successful transactions
            break
        except Exception as e:
            if session:
                session.rollback()  # Rollback failed transactions
                session_manager.return_session(session)
            if attempt < max_retries - 1:
                logger.warning(f"Database session error (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to get database session after {max_retries} attempts: {e}")
                raise
        finally:
            if session:
                session_manager.return_session(session)

# For backward compatibility
def get_session():
    return session_manager.get_session()

session = get_session

Base = declarative_base()