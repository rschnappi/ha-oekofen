"""
ÖkOfen Pellematic API Client - FIXED VERSION

Based on real-world analysis and successful curl testing.
Key insights:
- LOGIN: Uses application/x-www-form-urlencoded (form data)
- DATA REQUESTS: Uses application/json 
- Authentication via index.cgi with form data
- Data retrieval via /?action=get&attr=1 endpoint with JSON
- Must include User-Agent and XMLHttpRequest headers
"""
import logging
import json
import aiohttp
import async_timeout
from typing import Dict, Any, List, Optional

_LOGGER = logging.getLogger(__name__)

class PellematicAPI:
    """API client for ÖkOfen Pellematic heating systems."""
    
    def __init__(self, url: str, username: str, password: str, language: str = "de"):
        """Initialize the API client."""
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.language = language
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        
        # Core parameters for monitoring (based on successful testing)
        self.core_parameters = [
            "CAPPL:LOCAL.L_aussentemperatur_ist",           # Outside temperature
            "CAPPL:FA[0].L_kesselstatus",                   # Boiler status
            "CAPPL:FA[0].L_kesseltemperatur",               # Boiler temperature
            "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige",  # Boiler target temperature
            "CAPPL:FA[0].L_abgastemperatur",                # Exhaust temperature
            "CAPPL:LOCAL.L_hk[0].raumtemp_ist",             # Room temperature actual
            "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist",          # Flow temperature actual
            "CAPPL:LOCAL.L_ww[0].temp_ist",                 # Hot water temperature
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                cookie_jar=aiohttp.CookieJar()
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the ÖkOfen device.
        FIXED: Uses form-encoded data for login (like successful curl test).
        """
        session = await self._get_session()
        
        try:
            # Login data (proven working format)
            login_data = {
                'user': self.username,
                'pass': self.password,
                'submit': 'Anmelden'
            }
            
            # FIXED: Login uses form-encoded, NOT JSON!
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': f'{self.language},en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/x-www-form-urlencoded',  # FIXED: Form-encoded for login!
                'Origin': self.url,
                'Referer': f'{self.url}/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            _LOGGER.debug(f"Authenticating with {self.url}/index.cgi")
            
            async with async_timeout.timeout(15):
                async with session.post(
                    f"{self.url}/index.cgi",
                    data=login_data,  # FIXED: Send as form data, NOT JSON!
                    headers=headers,
                    allow_redirects=True
                ) as response:
                    
                    response_text = await response.text()
                    _LOGGER.debug(f"Login response status: {response.status}")
                    
                    # Check for successful authentication
                    if "LoginError=0" in response_text or response.status == 303:
                        # Check for session cookie
                        for cookie in session.cookie_jar:
                            if cookie.key == 'pksession':
                                _LOGGER.info("Authentication successful - session established")
                                self._authenticated = True
                                return True
                        
                        _LOGGER.warning("Login appeared successful but no session cookie found")
                        return False
                    else:
                        _LOGGER.error(f"Authentication failed - response: {response.status}")
                        if "LoginError" in response_text:
                            _LOGGER.error("Invalid credentials - check username and password")
                        return False
                        
        except Exception as e:
            _LOGGER.error(f"Authentication error: {e}")
            return False
    
    async def get_data(self, parameters: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get data from the ÖkOfen device.
        Uses JSON for data requests (based on successful curl testing).
        """
        if not self._authenticated:
            if not await self.authenticate():
                raise Exception("Authentication failed")
        
        session = await self._get_session()
        
        # Use provided parameters or default core parameters
        params_to_fetch = parameters or self.core_parameters
        
        try:
            # Data requests use JSON (based on jQuery analysis and successful curl)
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': self.language,
                'Content-Type': 'application/json',  # JSON for data requests
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.url}/',
                'Origin': self.url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            _LOGGER.debug(f"Fetching data for {len(params_to_fetch)} parameters")
            
            async with async_timeout.timeout(15):
                async with session.post(
                    f"{self.url}/?action=get&attr=1",
                    data=json.dumps(params_to_fetch),  # Send parameters as JSON array
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Parse response into dictionary
                        result = {}
                        if isinstance(response_data, list):
                            for item in response_data:
                                if isinstance(item, dict) and 'name' in item and 'value' in item:
                                    result[item['name']] = {
                                        'value': item['value'],
                                        'status': item.get('status', 'OK')
                                    }
                        
                        _LOGGER.debug(f"Successfully retrieved {len(result)} parameters")
                        return result
                    
                    elif response.status == 401:
                        # Re-authentication needed
                        _LOGGER.warning("Session expired, re-authenticating")
                        self._authenticated = False
                        if await self.authenticate():
                            return await self.get_data(parameters)
                        else:
                            raise Exception("Re-authentication failed")
                    
                    else:
                        _LOGGER.error(f"Data request failed with status {response.status}")
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            _LOGGER.error(f"Data retrieval error: {e}")
            raise
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._authenticated = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()