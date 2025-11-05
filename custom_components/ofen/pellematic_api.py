"""Pellematic API client for Home Assistant integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

class PellematicAPI:
    """API client for Pellematic heating systems."""
    
    def __init__(self, url: str, username: str, password: str, language: str = "de", debug_mode: bool = False) -> None:
        """Initialize the API client."""
        # Automatically add http:// if no protocol is specified
        if not url.startswith(('http://', 'https://')):
            url = f"http://{url}"
        
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.language = language
        self.debug_mode = debug_mode
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        
        # All parameters from the original script - we'll fetch everything!
        self.all_parameters = [
            "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek","CAPPL:LOCAL.heizkreisregler_vorhanden[0]","CAPPL:LOCAL.heizkreisregler_vorhanden[1]","CAPPL:LOCAL.heizkreisregler_vorhanden[2]","CAPPL:LOCAL.anlage_betriebsart","CAPPL:LOCAL.hk[0].vorhanden","CAPPL:LOCAL.hk[0].betriebsart[0]","CAPPL:LOCAL.hk[1].vorhanden","CAPPL:LOCAL.hk[1].betriebsart[0]","CAPPL:LOCAL.hk[2].vorhanden","CAPPL:LOCAL.hk[2].betriebsart[0]","CAPPL:LOCAL.hk[3].vorhanden","CAPPL:LOCAL.hk[3].betriebsart[0]","CAPPL:LOCAL.hk[4].vorhanden","CAPPL:LOCAL.hk[4].betriebsart[0]","CAPPL:LOCAL.hk[5].vorhanden","CAPPL:LOCAL.hk[5].betriebsart[0]","CAPPL:LOCAL.hk[0].betriebsart[1]","CAPPL:LOCAL.hk[1].betriebsart[1]","CAPPL:LOCAL.hk[2].betriebsart[1]","CAPPL:LOCAL.hk[3].betriebsart[1]","CAPPL:LOCAL.hk[4].betriebsart[1]","CAPPL:LOCAL.hk[5].betriebsart[1]","CAPPL:LOCAL.hk[0].betriebsart[2]","CAPPL:LOCAL.hk[1].betriebsart[2]","CAPPL:LOCAL.hk[2].betriebsart[2]","CAPPL:LOCAL.hk[3].betriebsart[2]","CAPPL:LOCAL.hk[4].betriebsart[2]","CAPPL:LOCAL.hk[5].betriebsart[2]","CAPPL:LOCAL.ww[0].vorhanden","CAPPL:LOCAL.ww[0].betriebsart[0]","CAPPL:LOCAL.ww[1].vorhanden","CAPPL:LOCAL.ww[1].betriebsart[0]","CAPPL:LOCAL.ww[2].vorhanden","CAPPL:LOCAL.ww[2].betriebsart[0]","CAPPL:LOCAL.ww[0].betriebsart[1]","CAPPL:LOCAL.ww[1].betriebsart[1]","CAPPL:LOCAL.ww[2].betriebsart[1]","CAPPL:LOCAL.ww[0].betriebsart[2]","CAPPL:LOCAL.ww[1].betriebsart[2]","CAPPL:LOCAL.ww[2].betriebsart[2]","CAPPL:LOCAL.sk[0].vorhanden","CAPPL:LOCAL.sk[0].betriebsart","CAPPL:LOCAL.sk[2].vorhanden","CAPPL:LOCAL.sk[2].betriebsart","CAPPL:LOCAL.sk[4].vorhanden","CAPPL:LOCAL.sk[4].betriebsart","CAPPL:LOCAL.sk[1].vorhanden","CAPPL:LOCAL.sk[1].betriebsart","CAPPL:LOCAL.sk[3].vorhanden","CAPPL:LOCAL.sk[3].betriebsart","CAPPL:LOCAL.sk[5].vorhanden","CAPPL:LOCAL.sk[5].betriebsart","CAPPL:LOCAL.pellematic_vorhanden[0]","CAPPL:FA[0].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[1]","CAPPL:FA[1].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[2]","CAPPL:FA[2].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[3]","CAPPL:FA[3].betriebsart_fa","CAPPL:LOCAL.fernwartung_einheit","CAPPL:LOCAL.L_aussentemperatur_ist","CAPPL:FA[0].L_kesselstatus","CAPPL:FA[1].L_kesselstatus","CAPPL:FA[2].L_kesselstatus","CAPPL:FA[3].L_kesselstatus","CAPPL:FA[0].L_kesseltemperatur","CAPPL:FA[0].L_kesseltemperatur_soll_anzeige","CAPPL:FA[1].L_kesseltemperatur","CAPPL:FA[1].L_kesseltemperatur_soll_anzeige","CAPPL:FA[2].L_kesseltemperatur","CAPPL:FA[2].L_kesseltemperatur_soll_anzeige","CAPPL:FA[3].L_kesseltemperatur","CAPPL:FA[3].L_kesseltemperatur_soll_anzeige","CAPPL:LOCAL.bestke_vorhanden","CAPPL:LOCAL.L_bestke_temp_ist","CAPPL:LOCAL.L_bestke_umschaltventil","CAPPL:LOCAL.pu[0].vorhanden","CAPPL:LOCAL.L_pu[0].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[0].einschaltfuehler_soll","CAPPL:LOCAL.pu[1].vorhanden","CAPPL:LOCAL.L_pu[1].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[1].einschaltfuehler_soll","CAPPL:LOCAL.pu[2].vorhanden","CAPPL:LOCAL.L_pu[2].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[2].einschaltfuehler_soll","CAPPL:LOCAL.L_pu[0].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[0].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[1].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[1].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[2].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[2].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[0].pumpe","CAPPL:LOCAL.L_pu[1].pumpe","CAPPL:LOCAL.L_pu[2].pumpe","CAPPL:LOCAL.L_zaehler_fehler"
        ]
        
        # Key parameters for normal operation (subset of all_parameters)
        self.key_parameters = [
            "CAPPL:LOCAL.L_aussentemperatur_ist",
            "CAPPL:FA[0].L_kesselstatus",
            "CAPPL:FA[0].L_kesseltemperatur",
            "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige",
            "CAPPL:FA[1].L_kesselstatus",
            "CAPPL:FA[1].L_kesseltemperatur", 
            "CAPPL:FA[1].L_kesseltemperatur_soll_anzeige",
            "CAPPL:FA[2].L_kesselstatus",
            "CAPPL:FA[2].L_kesseltemperatur",
            "CAPPL:FA[2].L_kesseltemperatur_soll_anzeige",
            "CAPPL:FA[3].L_kesselstatus",
            "CAPPL:FA[3].L_kesseltemperatur",
            "CAPPL:FA[3].L_kesseltemperatur_soll_anzeige",
            "CAPPL:LOCAL.L_bestke_temp_ist",
            "CAPPL:LOCAL.L_bestke_umschaltventil",
            "CAPPL:LOCAL.L_pu[0].pumpe",
            "CAPPL:LOCAL.L_pu[1].pumpe",
            "CAPPL:LOCAL.L_pu[2].pumpe",
            "CAPPL:LOCAL.L_zaehler_fehler",
            "CAPPL:LOCAL.anlage_betriebsart"
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
        return self._session
    
    async def authenticate(self) -> bool:
        """Authenticate with the Pellematic system."""
        session = await self._get_session()
        
        try:
            # Step 1: Get login page to establish session
            async with async_timeout.timeout(10):
                async with session.get(f"{self.url}/") as response:
                    response.raise_for_status()
                    _LOGGER.debug("Got login page successfully")
            
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
            
            async with async_timeout.timeout(10):
                async with session.post(
                    f"{self.url}/index.cgi",
                    data=login_data,
                    headers=headers,
                    allow_redirects=True
                ) as response:
                    response.raise_for_status()
                    
                    # Check for login error
                    if 'LoginError' in str(session.cookie_jar):
                        _LOGGER.error("Login failed - invalid credentials")
                        return False
                    
                    self._authenticated = True
                    _LOGGER.debug("Authentication successful")
                    return True
                    
        except Exception as e:
            _LOGGER.error(f"Authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def fetch_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data from the Pellematic system."""
        if not self._authenticated:
            if not await self.authenticate():
                return None
        
        session = await self._get_session()
        
        # Choose parameters based on debug mode
        parameters_to_fetch = self.all_parameters if self.debug_mode else self.key_parameters
        
        try:
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': self.language,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.url}/',
                'Origin': self.url
            }
            
            async with async_timeout.timeout(15):
                async with session.post(
                    f"{self.url}/?action=get&attr=1",
                    data=json.dumps(parameters_to_fetch),
                    headers=headers
                ) as response:
                    
                    if response.status == 403:
                        _LOGGER.warning("Access forbidden - re-authenticating")
                        self._authenticated = False
                        if await self.authenticate():
                            return await self.fetch_data()
                        return None
                    
                    response.raise_for_status()
                    data_array = await response.json()
                    
                    # Map parameters to values
                    result = {}
                    for i, param in enumerate(parameters_to_fetch):
                        if i < len(data_array):
                            result[param] = data_array[i]
                    
                    if self.debug_mode:
                        _LOGGER.info(f"DEBUG MODE: Retrieved {len(result)} data points")
                        # Log all parameter names and values for debugging
                        for param, value in result.items():
                            _LOGGER.info(f"DEBUG: {param} = {value}")
                    else:
                        _LOGGER.debug(f"Retrieved {len(result)} data points")
                    
                    return result
                    
        except Exception as e:
            _LOGGER.error(f"Failed to fetch data: {e}")
            self._authenticated = False
            return None
    
    async def get_parsed_data(self) -> Optional[Dict[str, Any]]:
        """Get data in a more user-friendly format."""
        raw_data = await self.fetch_data()
        if not raw_data:
            return None
        
        # In debug mode, return all raw data plus parsed data
        if self.debug_mode:
            parsed = {
                'debug_mode': True,
                'raw_data_count': len(raw_data),
                'raw_data': raw_data,  # Include all raw data for debugging
            }
            
            # Also add some parsed highlights for convenience
            parsed.update(self._parse_key_data(raw_data))
            return parsed
        
        # Normal mode - return only parsed key data
        return self._parse_key_data(raw_data)
    
    def _parse_key_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the key data points from raw data."""
        parsed = {
            'outside_temperature': raw_data.get("CAPPL:LOCAL.L_aussentemperatur_ist"),
            'buffer_tank_temperature': raw_data.get("CAPPL:LOCAL.L_bestke_temp_ist"),
            'error_count': raw_data.get("CAPPL:LOCAL.L_zaehler_fehler"),
            'system_mode': raw_data.get("CAPPL:LOCAL.anlage_betriebsart"),
            'boilers': [],
            'pumps': []
        }
        
        # Parse boiler data - check up to 4 boilers
        for i in range(4):
            status = raw_data.get(f"CAPPL:FA[{i}].L_kesselstatus")
            temp = raw_data.get(f"CAPPL:FA[{i}].L_kesseltemperatur")
            temp_target = raw_data.get(f"CAPPL:FA[{i}].L_kesseltemperatur_soll_anzeige")
            
            if status is not None or temp is not None:
                parsed['boilers'].append({
                    'index': i,
                    'status': status,
                    'temperature': temp,
                    'target_temperature': temp_target
                })
        
        # Parse pump data
        for i in range(3):
            pump_state = raw_data.get(f"CAPPL:LOCAL.L_pu[{i}].pumpe")
            if pump_state is not None:
                parsed['pumps'].append({
                    'index': i,
                    'running': bool(pump_state)
                })
        
        return parsed
    
    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._authenticated = False