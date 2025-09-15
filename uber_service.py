"""
Uber Fleet Supplier API Integration Service

This module provides OAuth 2.0 authentication and data synchronization 
with Uber's Fleet Supplier APIs for PLS TRAVELS.
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class UberAPIError(Exception):
    """Custom exception for Uber API errors"""
    pass

class SyncStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'

@dataclass
class UberConfig:
    """Uber API configuration"""
    client_id: str
    client_secret: str
    base_url: str = "https://api.uber.com"
    auth_url: str = "https://auth.uber.com/oauth/v2/token"
    scope: str = "fleet"

class UberFleetService:
    """
    Service class for interacting with Uber Fleet Supplier APIs
    """
    
    def __init__(self):
        self.config = UberConfig(
            client_id=os.environ.get("UBER_CLIENT_ID", ""),
            client_secret=os.environ.get("UBER_CLIENT_SECRET", "")
        )
        
        self.credentials_available = bool(self.config.client_id and self.config.client_secret)
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self.session = requests.Session()
        
        # Set default headers and timeouts for API calls
        self.session.headers.update({
            'User-Agent': 'PLS-TRAVELS/1.0'
        })
        
        # Configure session with timeout and retry settings
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]  # Only idempotent methods to prevent duplicate requests
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default timeout for all requests
        self.request_timeout = 15  # 15 seconds total timeout
    
    def authenticate(self) -> bool:
        """
        Authenticate with Uber APIs using OAuth 2.0 Client Credentials flow
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not self.credentials_available:
            logger.warning("Uber API credentials not configured")
            return False
            
        try:
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': self.config.client_id,
                'client_secret': self.config.client_secret,
                'scope': self.config.scope
            }
            
            logger.info("Attempting to authenticate with Uber Fleet APIs")
            # Use form data for authentication as per Uber API specification
            auth_headers = {
                'User-Agent': 'PLS-TRAVELS/1.0'
            }
            response = requests.post(
                self.config.auth_url, 
                data=auth_data, 
                headers=auth_headers,
                timeout=(5, 10)  # (connect_timeout, read_timeout)
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
                
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
                
                # Update session headers with access token and content type for API calls
                self.session.headers.update({
                    'Authorization': f'Bearer {self._access_token}',
                    'Content-Type': 'application/json'
                })
                
                logger.info("Successfully authenticated with Uber Fleet APIs")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        if not self._access_token or not self._token_expires_at:
            return self.authenticate()
        
        if datetime.utcnow() >= self._token_expires_at:
            logger.info("Access token expired, refreshing...")
            return self.authenticate()
        
        return True
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated request to Uber API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Dict: API response data
            
        Raises:
            UberAPIError: If request fails
        """
        if not self._ensure_authenticated():
            raise UberAPIError("Failed to authenticate with Uber APIs")
        
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            # Set timeout if not already provided
            if 'timeout' not in kwargs:
                kwargs['timeout'] = (5, self.request_timeout)
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code in [200, 201, 204]:
                return response.json() if response.content else {}
            elif response.status_code == 401:
                # Token might be expired, try to re-authenticate once
                if self.authenticate():
                    # Set timeout if not already provided
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = (5, self.request_timeout)
                    response = self.session.request(method, url, **kwargs)
                    if response.status_code in [200, 201, 204]:
                        return response.json() if response.content else {}
                
                raise UberAPIError(f"Authentication failed: {response.text}")
            else:
                raise UberAPIError(f"API request failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise UberAPIError(f"Request error: {str(e)}")
    
    def get_vehicles(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get fleet vehicles from Uber
        
        Args:
            limit: Number of vehicles to fetch (max 50)
            offset: Pagination offset
            
        Returns:
            List of vehicle data
        """
        endpoint = f"/v1/fleet/vehicles"
        params = {'limit': min(limit, 50), 'offset': offset}
        
        response = self._make_request('GET', endpoint, params=params)
        return response.get('vehicles', [])
    
    def get_drivers(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get fleet drivers from Uber
        
        Args:
            limit: Number of drivers to fetch (max 50)
            offset: Pagination offset
            
        Returns:
            List of driver data
        """
        endpoint = f"/v1/fleet/drivers"
        params = {'limit': min(limit, 50), 'offset': offset}
        
        response = self._make_request('GET', endpoint, params=params)
        return response.get('drivers', [])
    
    def get_trips(self, start_date: datetime, end_date: datetime, 
                  limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get fleet trip data from Uber
        
        Args:
            start_date: Start date for trip data
            end_date: End date for trip data
            limit: Number of trips to fetch (max 50)
            offset: Pagination offset
            
        Returns:
            List of trip data
        """
        endpoint = f"/v1/fleet/trips"
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'limit': min(limit, 50),
            'offset': offset
        }
        
        response = self._make_request('GET', endpoint, params=params)
        return response.get('trips', [])
    
    def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a vehicle in Uber fleet
        
        Args:
            vehicle_data: Vehicle information
            
        Returns:
            Created vehicle data
        """
        endpoint = "/v1/fleet/vehicles"
        response = self._make_request('POST', endpoint, json=vehicle_data)
        return response
    
    def update_vehicle(self, vehicle_id: str, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a vehicle in Uber fleet
        
        Args:
            vehicle_id: Uber vehicle ID
            vehicle_data: Updated vehicle information
            
        Returns:
            Updated vehicle data
        """
        endpoint = f"/v1/fleet/vehicles/{vehicle_id}"
        response = self._make_request('PUT', endpoint, json=vehicle_data)
        return response
    
    def create_driver(self, driver_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a driver in Uber fleet
        
        Args:
            driver_data: Driver information
            
        Returns:
            Created driver data
        """
        endpoint = "/v1/fleet/drivers"
        response = self._make_request('POST', endpoint, json=driver_data)
        return response
    
    def update_driver(self, driver_id: str, driver_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a driver in Uber fleet
        
        Args:
            driver_id: Uber driver ID
            driver_data: Updated driver information
            
        Returns:
            Updated driver data
        """
        endpoint = f"/v1/fleet/drivers/{driver_id}"
        response = self._make_request('PUT', endpoint, json=driver_data)
        return response

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Uber APIs
        
        Returns:
            Connection test results
        """
        if not self.credentials_available:
            return {
                'status': 'error',
                'message': 'Uber API credentials not configured. Please set UBER_CLIENT_ID and UBER_CLIENT_SECRET environment variables.',
                'authenticated': False
            }
            
        try:
            if self._ensure_authenticated():
                # Try to fetch a small amount of data to test the connection
                vehicles = self.get_vehicles(limit=1)
                return {
                    'status': 'success',
                    'message': 'Connection to Uber Fleet APIs successful',
                    'authenticated': True,
                    'test_data_count': len(vehicles)
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Failed to authenticate with Uber APIs',
                    'authenticated': False
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {str(e)}',
                'authenticated': False
            }

# Global service instance
try:
    uber_service = UberFleetService()
except Exception as e:
    logger.error(f"Failed to initialize Uber service: {str(e)}")
    # Create a dummy service that will handle missing credentials gracefully
    uber_service = None