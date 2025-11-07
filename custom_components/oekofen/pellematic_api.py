"""
ÖkOfen Pellematic API Client - VERIFIED WORKING

Based on real-world testing with actual ÖkOfen device (Nov 2025).
TESTED and WORKING configuration:

LOGIN (POST to /index.cgi):
- Content-Type: application/x-www-form-urlencoded
- Fields: username, password, language, submit
- Success: HTTP 303 + Set-Cookie: pksession=XXXXX + LoginError=0
- Device redirects / to login.cgi when not authenticated

DATA REQUESTS (POST to /?action=get&attr=1):
- Content-Type: application/json
- Body: JSON array of parameter names
- Must include session cookie from login
- X-Requested-With: XMLHttpRequest header required
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
            # Login data - TESTED and WORKING format for newer firmware
            # Uses: username/password/language/submit (not user/pass)
            login_data = {
                'username': self.username,
                'password': self.password,
                'language': self.language,
                'submit': 'Anmelden'
            }
            
            # Headers - NO Content-Type header! Let aiohttp set it correctly for form data
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': f'{self.language},en;q=0.5',
                'Origin': self.url,
                'Referer': f'{self.url}/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            _LOGGER.debug(f"Authenticating with {self.url}/index.cgi")
            _LOGGER.debug(f"Login data: username={self.username}, language={self.language}")
            
            async with async_timeout.timeout(15):
                async with session.post(
                    f"{self.url}/index.cgi",
                    data=login_data,  # aiohttp will auto-encode as application/x-www-form-urlencoded
                    headers=headers,
                    allow_redirects=False  # DON'T follow redirects - we need the 303 response with cookies!
                ) as response:
                    
                    response_text = await response.text()
                    _LOGGER.debug(f"Login response status: {response.status}")
                    _LOGGER.debug(f"Response URL: {response.url}")
                    _LOGGER.debug(f"Response headers: {dict(response.headers)}")
                    
                    # Check response cookies FIRST (these are set by the server in this response)
                    response_cookies = {}
                    for key, cookie in response.cookies.items():
                        response_cookies[key] = cookie.value
                    _LOGGER.debug(f"Response cookies: {response_cookies}")
                    
                    # Check for LoginError in response
                    login_error = response_cookies.get('LoginError', '')
                    if login_error == '1':
                        _LOGGER.error("Invalid credentials (LoginError=1) - check username/password")
                        _LOGGER.debug(f"Response text (first 500 chars): {response_text[:500]}")
                        return False
                    
                    # Check for pksession in response cookies (most reliable)
                    pksession = response_cookies.get('pksession', '')
                    if pksession:
                        _LOGGER.info(f"✓ Session cookie found in response: pksession={pksession}")
                        _LOGGER.info(f"✓ Authentication successful (Status: {response.status})")
                        self._authenticated = True
                        return True
                    
                    # Fallback: Check session.cookie_jar (in case cookies were already stored)
                    for cookie in session.cookie_jar:
                        if cookie.key == 'pksession':
                            _LOGGER.info(f"✓ Session cookie found in jar: pksession={cookie.value}")
                            _LOGGER.info(f"✓ Authentication successful (Status: {response.status})")
                            self._authenticated = True
                            return True
                    
                    # No session cookie found
                    _LOGGER.error(f"✗ Authentication failed - Status: {response.status}, No pksession cookie")
                    _LOGGER.debug(f"Response text (first 1000 chars): {response_text[:1000]}")
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