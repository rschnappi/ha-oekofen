"""
Enhanced Debug Version of ÖkOfen Integration
============================================

Diese Version fügt umfangreiche Debug-Ausgaben hinzu.
Ersetzen Sie temporär die pellematic_api.py mit dieser Version für mehr Debugging.

Um diese zu verwenden:
1. Sichern Sie Ihre aktuelle pellematic_api.py
2. Kopieren Sie diese Datei nach custom_components/ofen/pellematic_api.py  
3. Starten Sie Home Assistant neu
4. Prüfen Sie die Logs unter Settings -> System -> Logs
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)  # Force debug level

class PellematicAPI:
    """Debug version of Pellematic API client."""
    
    def __init__(self, url: str, username: str, password: str, language: str = "de", debug_mode: bool = True) -> None:
        """Initialize the API client with enhanced debugging."""
        if not url.startswith(('http://', 'https://')):
            url = f"http://{url}"
        
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.language = language
        self.debug_mode = True  # Force debug mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        
        # Enhanced underpressure parameter list
        self.underpressure_test_parameters = [
            "CAPPL:FA[0].unterdruck_modus",
            "CAPPL:FA[0].L_unterdruck", 
            "CAPPL:FA[0].unterdruck_sollwert",
            "CAPPL:FA[0].unterdruck_istwert",
            "CAPPL:FA[0].L_unterdruck_soll",
            "CAPPL:FA[0].L_unterdruck_ist",
            "CAPPL:FA[0].saugzug_unterdruck",
            "CAPPL:FA[0].unterdruck_sensor",
            "CAPPL:FA[0].unterdruck",
            "CAPPL:FA[0].L_saugzugdrehzahl",
            "CAPPL:FA[0].L_luefterdrehzahl",
        ]
        
        _LOGGER.error("🔥 ENHANCED DEBUG MODE ACTIVATED")
        _LOGGER.error(f"🔗 Target URL: {self.url}")
        _LOGGER.error(f"👤 Username: {self.username}")
        _LOGGER.error(f"🔍 Testing {len(self.underpressure_test_parameters)} underpressure parameters")
    
    async def test_underpressure_parameters(self) -> Dict[str, Any]:
        """Test underpressure parameters individually."""
        _LOGGER.error("🧪 TESTING UNDERPRESSURE PARAMETERS")
        
        if not self._authenticated:
            _LOGGER.error("❌ Not authenticated, attempting login...")
            if not await self.authenticate():
                _LOGGER.error("❌ Authentication failed!")
                return {}
        
        session = await self._get_session()
        results = {}
        
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': self.language,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'{self.url}/',
            'Origin': self.url
        }
        
        # Test each parameter individually
        for param in self.underpressure_test_parameters:
            try:
                _LOGGER.error(f"🔍 Testing parameter: {param}")
                
                async with async_timeout.timeout(5):
                    async with session.post(
                        f"{self.url}/?action=get&attr=1",
                        data=json.dumps([param]),
                        headers=headers
                    ) as response:
                        _LOGGER.error(f"📡 Response status for {param}: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            _LOGGER.error(f"📊 Raw response for {param}: {data}")
                            
                            if data and len(data) > 0 and data[0] is not None:
                                result = data[0]
                                if isinstance(result, dict) and 'value' in result:
                                    value = result['value']
                                    _LOGGER.error(f"✅ SUCCESS: {param} = {value}")
                                    if result.get('shortText'):
                                        _LOGGER.error(f"   📝 Description: {result['shortText']}")
                                    if result.get('unitText'):
                                        _LOGGER.error(f"   📏 Unit: {result['unitText']}")
                                    results[param] = result
                                else:
                                    _LOGGER.error(f"❌ {param}: Invalid response format: {result}")
                            else:
                                _LOGGER.error(f"❌ {param}: Empty or null response")
                        else:
                            response_text = await response.text()
                            _LOGGER.error(f"❌ {param}: HTTP {response.status} - {response_text}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                _LOGGER.error(f"❌ {param}: Exception - {e}")
                import traceback
                _LOGGER.error(f"Stack trace: {traceback.format_exc()}")
        
        _LOGGER.error(f"🎯 UNDERPRESSURE TEST COMPLETE: Found {len(results)} working parameters")
        return results
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                cookie_jar=cookie_jar,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """Authenticate with enhanced logging."""
        _LOGGER.error("🔐 Starting authentication process...")
        session = await self._get_session()
        
        try:
            # Step 1: Get login page
            _LOGGER.error(f"📡 Getting login page: {self.url}/")
            async with async_timeout.timeout(10):
                async with session.get(f"{self.url}/") as response:
                    response.raise_for_status()
                    _LOGGER.error(f"✅ Login page: HTTP {response.status}")
            
            # Step 2: Perform login
            login_data = {
                'username': self.username,
                'password': self.password,
                'language': self.language,
                'submit': 'Anmelden'
            }
            
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': f'{self.language},en;q=0.5',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.url,
                'Referer': f'{self.url}/',
            }
            
            _LOGGER.error(f"📡 Posting login data to: {self.url}/index.cgi")
            async with async_timeout.timeout(10):
                async with session.post(
                    f"{self.url}/index.cgi",
                    data=login_data,
                    headers=headers,
                    allow_redirects=True
                ) as response:
                    response.raise_for_status()
                    _LOGGER.error(f"✅ Login response: HTTP {response.status}")
                    
                    # Check cookies
                    cookies = dict(session.cookie_jar)
                    _LOGGER.error(f"🍪 Cookies after login: {cookies}")
                    
                    if 'LoginError' in str(session.cookie_jar):
                        _LOGGER.error("❌ Login failed - invalid credentials")
                        return False
                    
                    self._authenticated = True
                    _LOGGER.error("✅ Authentication successful!")
                    
                    # Immediately test underpressure parameters
                    await self.test_underpressure_parameters()
                    
                    return True
                    
        except Exception as e:
            _LOGGER.error(f"❌ Authentication failed: {e}")
            import traceback
            _LOGGER.error(f"Stack trace: {traceback.format_exc()}")
            self._authenticated = False
            return False
    
    async def fetch_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data with enhanced logging."""
        _LOGGER.error("📊 Starting data fetch...")
        
        if not self._authenticated:
            if not await self.authenticate():
                return None
        
        # Return minimal data for now, focus on debugging
        return {"debug": "Enhanced debug mode active", "authenticated": True}
    
    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._authenticated = False
        _LOGGER.error("🔌 Session closed")