from typing import Dict, Optional
from datetime import datetime, timedelta
import aiohttp
import base64
import logging
from sqlalchemy.orm import Session
from models import RemoteServer

logger = logging.getLogger(__name__)

class RemoteAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.session = None

    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def authenticate(self, server: RemoteServer) -> Optional[str]:
        """Authenticate with a remote server and return the auth token."""
        try:
            if server.auth_type == "basic":
                return await self._handle_basic_auth(server)
            elif server.auth_type == "token":
                return await self._handle_token_auth(server)
            else:
                logger.error(f"Unsupported auth type: {server.auth_type}")
                return None
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None

    async def _handle_basic_auth(self, server: RemoteServer) -> str:
        """Handle basic authentication."""
        if not server.username or not server.password:
            logger.error("Username or password missing for basic auth")
            return None

        # Create basic auth header
        credentials = f"{server.username}:{server.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _handle_token_auth(self, server: RemoteServer) -> Optional[str]:
        """Handle token-based authentication."""
        # Check if we have a valid token
        if (server.access_token and server.token_expires_at and 
            server.token_expires_at > datetime.utcnow()):
            return server.access_token

        # Need to get a new token
        if not server.token_endpoint:
            logger.error("Token endpoint not configured")
            return None

        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Prepare token request
            token_url = f"{server.base_url.rstrip('/')}/{server.token_endpoint.lstrip('/')}"
            auth_data = {
                "username": server.username,
                "password": server.password
            }

            async with self.session.post(token_url, json=auth_data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    access_token = token_data.get("access_token")
                    expires_in = token_data.get("expires_in", 3600)  # Default 1 hour

                    # Update server with new token
                    server.access_token = access_token
                    server.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    self.db.commit()

                    return access_token
                else:
                    logger.error(f"Token request failed with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Token authentication failed: {str(e)}")
            return None

    async def refresh_token(self, server: RemoteServer) -> Optional[str]:
        """Refresh the access token for a server."""
        if server.auth_type != "token":
            return None

        # Clear existing token
        server.access_token = None
        server.token_expires_at = None
        self.db.commit()

        # Get new token
        return await self._handle_token_auth(server)

    async def get_auth_headers(self, server: RemoteServer) -> Dict[str, str]:
        """Get authentication headers for a remote server."""
        headers = {}
        
        if server.auth_type == "basic" and server.username and server.password:
            # Basic authentication
            auth_str = f"{server.username}:{server.password}"
            auth_bytes = auth_str.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            headers['Authorization'] = f'Basic {base64_auth}'
            
        elif server.auth_type == "token":
            # Token-based authentication
            if not server.access_token or self._is_token_expired(server):
                await self._refresh_token(server)
            headers['Authorization'] = f'Bearer {server.access_token}'
            
        elif server.api_key:
            # API key authentication
            headers['X-API-Key'] = server.api_key
            
        return headers

    def _is_token_expired(self, server: RemoteServer) -> bool:
        """Check if the access token is expired."""
        if not server.token_expires_at:
            return True
        return datetime.utcnow() >= server.token_expires_at

    async def _refresh_token(self, server: RemoteServer) -> None:
        """Refresh the access token for token-based authentication."""
        try:
            import httpx
            
            # Prepare token request
            token_data = {
                "username": server.username,
                "password": server.password
            }
            
            # Make token request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{server.base_url}{server.token_endpoint}",
                    json=token_data
                )
                response.raise_for_status()
                
                # Update server with new token
                token_info = response.json()
                server.access_token = token_info['access_token']
                server.token_expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Error refreshing token for server {server.id}: {str(e)}")
            raise 