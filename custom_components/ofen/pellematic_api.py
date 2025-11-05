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
            # Basis Systemparameter - VERIFIED WORKING FROM CURL
            "CAPPL:LOCAL.L_aussentemperatur_ist",
            "CAPPL:FA[0].L_kesselstatus",
            "CAPPL:FA[0].L_kesseltemperatur",
            "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige",
            "CAPPL:FA[0].L_abgastemperatur",
            "CAPPL:FA[0].L_abgastemperatur_vorhanden",
            "CAPPL:FA[0].L_feuerraumtemperatur",
            "CAPPL:FA[0].L_feuerraumtemperatur_vorhanden",
            "CAPPL:FA[0].L_feuerraumtemperatur_soll",
            "CAPPL:LOCAL.L_bestke_temp_ist",
            "CAPPL:LOCAL.L_bestke_umschaltventil",
            "CAPPL:LOCAL.L_pu[0].pumpe",
            "CAPPL:LOCAL.L_pu[1].pumpe",
            "CAPPL:LOCAL.L_pu[2].pumpe",
            "CAPPL:LOCAL.L_zaehler_fehler",
            "CAPPL:LOCAL.anlage_betriebsart",
            
            # System und Fernwartung - FROM CURL
            "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek",
            "CAPPL:LOCAL.fernwartung_einheit",
            "CAPPL:LOCAL.pellematic_vorhanden[0]",
            
            # CRITICAL: Fan and Underpressure - FROM YOUR CURL REQUEST
            "CAPPL:FA[0].L_luefterdrehzahl",
            "CAPPL:FA[0].L_saugzugdrehzahl", 
            "CAPPL:FA[0].unterdruck_modus",
            "CAPPL:FA[0].L_unterdruck",
            
            # Betriebszeiten - FROM CURL
            "CAPPL:FA[0].L_einschublaufzeit",
            "CAPPL:FA[0].L_pausenzeit",
            "CAPPL:FA[0].L_pe_schnecke_sauganlage",
            "CAPPL:FA[0].L_saugintervall",
            
            # TURBINE PARAMETERS - FROM YOUR WORKING CURL
            "CAPPL:FA[0].L_cmp_fa",
            "CAPPL:FA[0].rm_reinigungszeit1_befuellung",
            "CAPPL:FA[0].rm_reinigungszeit1_befuellung_cmp",
            "CAPPL:FA[0].turbine_takt_ra_vacuum",
            "CAPPL:FA[0].turbine_pause_ra_vacuum",
            "CAPPL:FA[0].turbine_saugintervall",
            "CAPPL:FA[0].turbine_saugzeit_max",
            "CAPPL:FA[0].turbine_nachlauf",
            
            # Heizkreis-Parameter (erweitert)
            "CAPPL:LOCAL.hk[0].betriebsart[1]",
            "CAPPL:LOCAL.hk[0].raumtemp_heizen",
            "CAPPL:LOCAL.hk[0].raumtemp_absenken",
            "CAPPL:LOCAL.hk[0].aktives_zeitprogramm",
            "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist",
            "CAPPL:LOCAL.L_hk[0].vorlauftemp_soll",
            "CAPPL:LOCAL.L_hk[0].raumtemp_ist",
            "CAPPL:LOCAL.L_hk[0].raumtemp_soll",
            "CAPPL:LOCAL.L_hk[0].pumpe",
            # Heizkurven-Parameter
            "CAPPL:LOCAL.hk[0].heizkurve_steigung",
            "CAPPL:LOCAL.hk[0].heizkurve_fusspunkt",
            "CAPPL:LOCAL.hk[0].heizgrenze_heizen",
            "CAPPL:LOCAL.hk[0].heizgrenze_absenken",
            "CAPPL:LOCAL.hk[0].vorhaltezeit",
            "CAPPL:LOCAL.hk[0].raumfuehler_einfluss",
            "CAPPL:LOCAL.hk[0].raumtemp_plus",
            "CAPPL:LOCAL.hk[0].raumfuehler_zuweisung",
            # Erweiterte Heizkreise (falls vorhanden)
            "CAPPL:LOCAL.hk[1].betriebsart[1]",
            "CAPPL:LOCAL.L_hk[1].vorlauftemp_ist",
            "CAPPL:LOCAL.L_hk[1].vorlauftemp_soll",
            
            # Warmwasser-Parameter - FROM YOUR CURL
            "CAPPL:LOCAL.ww[0].betriebsart[1]",
            "CAPPL:LOCAL.ww[0].solltemp_komfort",
            "CAPPL:LOCAL.ww[0].solltemp_reduziert",
            "CAPPL:LOCAL.ww[0].aktives_zeitprogramm",
            "CAPPL:LOCAL.L_ww[0].temp_ist",
            "CAPPL:LOCAL.L_ww[0].temp_soll",
            "CAPPL:LOCAL.L_ww[0].ladepumpe",
            "CAPPL:LOCAL.L_ww[0].durchlauferhitzer",
            "CAPPL:LOCAL.L_ww[0].wwauto",
            "CAPPL:LOCAL.L_ww[0].wweinmalladung",
            "CAPPL:LOCAL.ww[0].waermepumpe_mode",
            "CAPPL:LOCAL.ww[0].temperaturband",
            "CAPPL:LOCAL.ww[0].einschaltdifferenz",
            "CAPPL:LOCAL.ww[0].ausschaltdifferenz",
            
            # ASH and CLEANING Parameters - FROM YOUR CURL  
            "CAPPL:FA[0].rm_reinigungsmodul_aktiv",
            "CAPPL:FA[0].L_rm_status_tuere_reinigungsmodul",
            "CAPPL:FA[0].L_rm_status_austragung",
            "CAPPL:FA[0].L_rm_status_reinigung",
            "CAPPL:FA[0].L_rm_position_reinigungsmodul",
            "CAPPL:FA[0].rm_befuellung_zeit",
            "CAPPL:FA[0].rm_befuellung_dauer",
            "CAPPL:FA[0].L_asche_wiegung_vorhanden",
            "CAPPL:FA[0].L_asche_gewicht",
            "CAPPL:FA[0].asche_maxgewicht",
            "CAPPL:FA[0].asche_warnschwelle"
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=False)
            timeout = aiohttp.ClientTimeout(total=30)
            # Create explicit cookie jar to ensure cookies are saved
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
    
    async def _visit_contexts(self) -> None:
        """Visit different contexts to ensure all parameters are loaded."""
        session = await self._get_session()
        
        # Different approaches to load parameters from various contexts
        try:
            # Method 1: Try visiting hash URLs (frontend routing)
            hash_contexts = [
                f"{self.url}/#/pellematic.0",           # Main pellematic context
                f"{self.url}/#/pellematic.0/turbine",   # Turbine parameters
                f"{self.url}/#/pellematic.0/entaschung", # Ash removal parameters
                f"{self.url}/#/pellematic.0/reinigung",  # Cleaning parameters
                f"{self.url}/#/heizkreis.0",            # Heating circuit details
                f"{self.url}/#/warmwasser.0",           # Hot water details
            ]
            
            for context_url in hash_contexts:
                try:
                    async with async_timeout.timeout(3):
                        async with session.get(context_url) as response:
                            _LOGGER.debug(f"Visited context: {context_url}")
                            await asyncio.sleep(0.1)
                except Exception as e:
                    _LOGGER.debug(f"Hash URL visit failed {context_url}: {e}")
                    continue
            
            # Method 2: Try to load specific parameter sets to trigger context loading
            context_parameters = [
                # Turbine parameters
                ["CAPPL:FA[0].turbine_takt_ra_vacuum", "CAPPL:FA[0].turbine_pause_ra_vacuum"],
                # Ash parameters  
                ["CAPPL:FA[0].asche_externe_aschebox", "CAPPL:FA[0].L_drehzahl_ascheschnecke_ist"],
                # Heating circuit parameters
                ["CAPPL:LOCAL.L_hk[0].raumtemp_ist", "CAPPL:LOCAL.L_hk[0].vorlauftemp_ist"],
                # Hot water parameters
                ["CAPPL:LOCAL.ww[0].betriebsart[1]", "CAPPL:LOCAL.L_ww[0].temp_soll"],
                # Underpressure and fan parameters - try different variations
                ["CAPPL:FA[0].unterdruck_modus", "CAPPL:FA[0].L_unterdruck"],
                ["CAPPL:FA[0].L_luefterdrehzahl", "CAPPL:FA[0].L_saugzugdrehzahl"],
                # Alternative underpressure parameter names to test
                ["CAPPL:FA[0].unterdruck", "CAPPL:FA[0].saugzug_unterdruck"],
                ["CAPPL:FA[0].L_unterdruck_ist", "CAPPL:FA[0].L_unterdruck_soll"],
            ]
            
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': self.language,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.url}/',
                'Origin': self.url
            }
            
            # Pre-load specific parameter groups
            for param_group in context_parameters:
                try:
                    async with async_timeout.timeout(5):
                        async with session.post(
                            f"{self.url}/?action=get&attr=1",
                            data=json.dumps(param_group),
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                await response.json()  # Read and discard, just to trigger loading
                                _LOGGER.debug(f"Pre-loaded parameter group: {param_group[:2]}...")
                            await asyncio.sleep(0.1)
                except Exception as e:
                    _LOGGER.debug(f"Parameter group pre-load failed: {e}")
                    continue
                    
        except Exception as e:
            _LOGGER.warning(f"Error visiting contexts: {e}")
    
    async def fetch_data(self) -> Optional[Dict[str, Any]]:
        """Fetch data from the Pellematic system."""
        if not self._authenticated:
            if not await self.authenticate():
                return None
        
        session = await self._get_session()
        
        # Visit different contexts to load all parameters
        await self._visit_contexts()
        
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
                    
                    # Map parameters to values - extract and format values correctly
                    result = {}
                    missing_parameters = []
                    
                    for i, param in enumerate(parameters_to_fetch):
                        if i < len(data_array):
                            api_object = data_array[i]
                            if isinstance(api_object, dict) and 'value' in api_object:
                                # Extract value and metadata
                                value = api_object['value']
                                divisor = api_object.get('divisor', '')
                                format_texts = api_object.get('formatTexts', '')
                                
                                # Handle different value types
                                processed_value = self._process_api_value(value, divisor, format_texts, param)
                                result[param] = processed_value
                                
                                # Store additional metadata for complex values
                                if format_texts or api_object.get('shortText'):
                                    result[f"{param}_meta"] = {
                                        'raw_value': value,
                                        'format_texts': format_texts,
                                        'short_text': api_object.get('shortText', ''),
                                        'unit_text': api_object.get('unitText', ''),
                                        'status': api_object.get('status', ''),
                                        'processed_value': processed_value
                                    }
                            else:
                                # Fallback for non-dict responses or missing data
                                if api_object is None or (isinstance(api_object, dict) and not api_object.get('value')):
                                    missing_parameters.append(param)
                                    _LOGGER.warning(f"Parameter {param} returned no data or invalid response: {api_object}")
                                else:
                                    result[param] = api_object
                        else:
                            missing_parameters.append(param)
                            _LOGGER.warning(f"Parameter {param} not found in API response")
                    
                    if missing_parameters:
                        _LOGGER.info(f"Missing/unavailable parameters: {missing_parameters}")
                    
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
    
    async def set_parameter(self, parameter: str, value: str) -> bool:
        """Set a parameter value on the Pellematic system."""
        if not self._authenticated:
            if not await self.authenticate():
                return False
        
        session = await self._get_session()
        
        try:
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': self.language,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.url}/',
                'Origin': self.url
            }
            
            # Prepare the data payload as shown in your curl example
            data_payload = {parameter: value}
            
            async with async_timeout.timeout(10):
                async with session.post(
                    f"{self.url}/?action=set",
                    data=json.dumps(data_payload),
                    headers=headers
                ) as response:
                    
                    if response.status == 403:
                        _LOGGER.warning("Access forbidden during parameter set - re-authenticating")
                        self._authenticated = False
                        if await self.authenticate():
                            return await self.set_parameter(parameter, value)
                        return False
                    
                    response.raise_for_status()
                    
                    # Check if the response indicates success
                    try:
                        result = await response.json()
                        _LOGGER.info(f"Successfully set parameter {parameter} = {value}")
                        _LOGGER.debug(f"Set parameter response: {result}")
                        return True
                    except:
                        # Some APIs might return empty or non-JSON response on success
                        if response.status == 200:
                            _LOGGER.info(f"Successfully set parameter {parameter} = {value}")
                            return True
                        else:
                            _LOGGER.error(f"Unexpected response status for set parameter: {response.status}")
                            return False
                    
        except Exception as e:
            _LOGGER.error(f"Failed to set parameter {parameter} = {value}: {e}")
            return False
    
    async def set_hot_water_mode(self, hw_index: int, mode: str) -> bool:
        """Set hot water operating mode. 
        
        Args:
            hw_index: Hot water circuit index (usually 0)
            mode: Operating mode - "0" for Off, "1" for Heat, "2" for Auto
        """
        parameter = f"CAPPL:LOCAL.ww[{hw_index}].betriebsart[1]"
        return await self.set_parameter(parameter, mode)
    
    async def set_heating_circuit_mode(self, hc_index: int, mode: str) -> bool:
        """Set heating circuit operating mode.
        
        Args:
            hc_index: Heating circuit index (usually 0)
            mode: Operating mode value
        """
        parameter = f"CAPPL:LOCAL.L_hk[{hc_index}].betriebsart"
        return await self.set_parameter(parameter, mode)
    
    async def set_room_temperature(self, hc_index: int, temperature: float) -> bool:
        """Set target room temperature for heating circuit.
        
        Args:
            hc_index: Heating circuit index
            temperature: Target temperature in Celsius
        """
        parameter = f"CAPPL:LOCAL.L_hk[{hc_index}].raumtemp_soll"
        return await self.set_parameter(parameter, str(temperature))
    
    async def set_hot_water_temperature(self, hw_index: int, temp_type: str, temperature: float) -> bool:
        """Set hot water temperature.
        
        Args:
            hw_index: Hot water circuit index
            temp_type: "heizen" or "absenken"
            temperature: Target temperature in Celsius
        """
        parameter = f"CAPPL:LOCAL.ww[{hw_index}].temp_{temp_type}"
        return await self.set_parameter(parameter, str(temperature))
    
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
    
    def _process_api_value(self, value: str, divisor: str, format_texts: str, param_name: str) -> Any:
        """Process API value based on type and formatting."""
        try:
            # Handle status values with formatTexts (like boiler status)
            if format_texts and format_texts.strip():
                try:
                    # Split formatTexts by | and get the text for this value
                    text_options = format_texts.split('|')
                    value_index = int(value)
                    if 0 <= value_index < len(text_options):
                        status_text = text_options[value_index].strip()
                        return {
                            'numeric_value': value_index,
                            'text_value': status_text,
                            'raw_value': value
                        }
                except (ValueError, IndexError):
                    pass
            
            # Handle timestamp values (very large numbers that look like unix timestamps)
            if '.' in value and len(value.split('.')[0]) >= 10:  # Unix timestamp detection
                try:
                    timestamp = float(value)
                    if timestamp > 1000000000:  # Valid unix timestamp range
                        import datetime
                        dt = datetime.datetime.fromtimestamp(timestamp)
                        return {
                            'timestamp': timestamp,
                            'datetime': dt.isoformat(),
                            'readable': dt.strftime('%Y-%m-%d %H:%M:%S')
                        }
                except (ValueError, OSError):
                    pass
            
            # Handle numeric values with divisor
            if divisor and divisor.strip() and divisor != '1':
                try:
                    return float(value) / float(divisor)
                except (ValueError, TypeError, ZeroDivisionError):
                    pass
            
            # Try to convert to float for simple numeric values
            try:
                return float(value)
            except (ValueError, TypeError):
                pass
            
            # Return as string if nothing else works
            return value
            
        except Exception as e:
            _LOGGER.warning(f"Error processing value for {param_name}: {e}")
            return value

    def _parse_key_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the key data points from raw data."""
        parsed = {
            'outside_temperature': raw_data.get("CAPPL:LOCAL.L_aussentemperatur_ist"),
            'buffer_tank_temperature': raw_data.get("CAPPL:LOCAL.L_bestke_temp_ist"),
            'error_count': raw_data.get("CAPPL:LOCAL.L_zaehler_fehler"),
            'system_mode': raw_data.get("CAPPL:LOCAL.anlage_betriebsart"),
            'maintenance_timestamp': raw_data.get("CAPPL:LOCAL.L_fernwartung_datum_zeit_sek"),
            'boilers': [],
            'pumps': [],
            'heating_circuits': [],
            'hot_water': []
        }
        
        # Parse boiler data - check up to 4 boilers
        for i in range(4):
            status = raw_data.get(f"CAPPL:FA[{i}].L_kesselstatus")
            temp = raw_data.get(f"CAPPL:FA[{i}].L_kesseltemperatur")
            temp_target = raw_data.get(f"CAPPL:FA[{i}].L_kesseltemperatur_soll_anzeige")
            
            if status is not None or temp is not None:
                # Extract meaningful status text if available
                status_text = None
                status_numeric = None
                if isinstance(status, dict) and 'text_value' in status:
                    status_text = status['text_value']
                    status_numeric = status['numeric_value']
                elif status is not None:
                    status_numeric = status
                
                parsed['boilers'].append({
                    'index': i,
                    'status_numeric': status_numeric,
                    'status_text': status_text,
                    'status_raw': status,
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
        
        # Parse heating circuit data - check up to 2 heating circuits
        for i in range(2):
            hc_mode = raw_data.get(f"CAPPL:LOCAL.hk[{i}].betriebsart[1]")
            hc_temp_heat = raw_data.get(f"CAPPL:LOCAL.hk[{i}].raumtemp_heizen")
            hc_temp_lower = raw_data.get(f"CAPPL:LOCAL.hk[{i}].raumtemp_absenken")
            hc_active_program = raw_data.get(f"CAPPL:LOCAL.hk[{i}].aktives_zeitprogramm")
            hc_flow_temp_actual = raw_data.get(f"CAPPL:LOCAL.L_hk[{i}].vorlauftemp_ist")
            hc_flow_temp_target = raw_data.get(f"CAPPL:LOCAL.L_hk[{i}].vorlauftemp_soll")
            hc_room_temp_actual = raw_data.get(f"CAPPL:LOCAL.L_hk[{i}].raumtemp_ist")
            hc_room_temp_target = raw_data.get(f"CAPPL:LOCAL.L_hk[{i}].raumtemp_soll")
            hc_pump = raw_data.get(f"CAPPL:LOCAL.L_hk[{i}].pumpe")
            
            # Heizkurven und erweiterte Parameter
            hc_heating_curve_slope = raw_data.get(f"CAPPL:LOCAL.hk[{i}].heizkurve_steigung")
            hc_heating_curve_foot = raw_data.get(f"CAPPL:LOCAL.hk[{i}].heizkurve_fusspunkt")
            hc_heating_limit_heat = raw_data.get(f"CAPPL:LOCAL.hk[{i}].heizgrenze_heizen")
            hc_heating_limit_lower = raw_data.get(f"CAPPL:LOCAL.hk[{i}].heizgrenze_absenken")
            hc_lead_time = raw_data.get(f"CAPPL:LOCAL.hk[{i}].vorhaltezeit")
            hc_room_sensor_influence = raw_data.get(f"CAPPL:LOCAL.hk[{i}].raumfuehler_einfluss")
            hc_room_temp_plus = raw_data.get(f"CAPPL:LOCAL.hk[{i}].raumtemp_plus")
            hc_room_sensor_assignment = raw_data.get(f"CAPPL:LOCAL.hk[{i}].raumfuehler_zuweisung")
            
            # Only add heating circuit if we have at least some data
            if any(x is not None for x in [hc_mode, hc_temp_heat, hc_flow_temp_actual, hc_room_temp_actual, hc_pump, hc_heating_curve_slope]):
                # Extract mode text if available
                mode_text = None
                mode_numeric = None
                if isinstance(hc_mode, dict) and 'text_value' in hc_mode:
                    mode_text = hc_mode['text_value']
                    mode_numeric = hc_mode['numeric_value']
                elif hc_mode is not None:
                    mode_numeric = hc_mode

                # Extract program text if available
                program_text = None
                program_numeric = None
                if isinstance(hc_active_program, dict) and 'text_value' in hc_active_program:
                    program_text = hc_active_program['text_value']
                    program_numeric = hc_active_program['numeric_value']
                elif hc_active_program is not None:
                    program_numeric = hc_active_program
                
                parsed['heating_circuits'].append({
                    'index': i,
                    'mode_numeric': mode_numeric,
                    'mode_text': mode_text,
                    'mode_raw': hc_mode,
                    'room_temp_heating': hc_temp_heat,
                    'room_temp_lowering': hc_temp_lower,
                    'active_program_numeric': program_numeric,
                    'active_program_text': program_text,
                    'active_program_raw': hc_active_program,
                    'flow_temp_actual': hc_flow_temp_actual,
                    'flow_temp_target': hc_flow_temp_target,
                    'room_temp_actual': hc_room_temp_actual,
                    'room_temp_target': hc_room_temp_target,
                    'pump_running': bool(hc_pump) if hc_pump is not None else None,
                    # Heizkurven-Parameter
                    'heating_curve_slope': hc_heating_curve_slope,
                    'heating_curve_foot_point': hc_heating_curve_foot,
                    'heating_limit_heat': hc_heating_limit_heat,
                    'heating_limit_lower': hc_heating_limit_lower,
                    'lead_time': hc_lead_time,
                    'room_sensor_influence': hc_room_sensor_influence,
                    'room_temp_plus': hc_room_temp_plus,
                    'room_sensor_assignment': hc_room_sensor_assignment
                })
        
        # Parse hot water data - check hot water circuit 0
        hw_mode = raw_data.get("CAPPL:LOCAL.ww[0].betriebsart[1]")
        hw_once_prepare = raw_data.get("CAPPL:LOCAL.ww[0].einmal_aufbereiten")
        hw_temp_heat = raw_data.get("CAPPL:LOCAL.ww[0].temp_heizen")
        hw_temp_lower = raw_data.get("CAPPL:LOCAL.ww[0].temp_absenken")
        hw_active_program = raw_data.get("CAPPL:LOCAL.ww[0].aktives_zeitprogramm")
        hw_switch_on_sensor = raw_data.get("CAPPL:LOCAL.L_ww[0].einschaltfuehler_ist")
        hw_temp_target = raw_data.get("CAPPL:LOCAL.L_ww[0].temp_soll")
        hw_switch_off_sensor = raw_data.get("CAPPL:LOCAL.L_ww[0].ausschaltfuehler_ist")
        hw_pump = raw_data.get("CAPPL:LOCAL.L_ww[0].pumpe")
        
        # Only add hot water if we have at least some data
        if any(x is not None for x in [hw_mode, hw_temp_heat, hw_temp_target, hw_pump]):
            # Extract mode text if available
            hw_mode_text = None
            hw_mode_numeric = None
            if isinstance(hw_mode, dict) and 'text_value' in hw_mode:
                hw_mode_text = hw_mode['text_value']
                hw_mode_numeric = hw_mode['numeric_value']
            elif hw_mode is not None:
                hw_mode_numeric = hw_mode

            # Extract program text if available
            hw_program_text = None
            hw_program_numeric = None
            if isinstance(hw_active_program, dict) and 'text_value' in hw_active_program:
                hw_program_text = hw_active_program['text_value']
                hw_program_numeric = hw_active_program['numeric_value']
            elif hw_active_program is not None:
                hw_program_numeric = hw_active_program
            
            parsed['hot_water'].append({
                'index': 0,
                'mode_numeric': hw_mode_numeric,
                'mode_text': hw_mode_text,
                'mode_raw': hw_mode,
                'once_prepare': bool(hw_once_prepare) if hw_once_prepare is not None else None,
                'temp_heating': hw_temp_heat,
                'temp_lowering': hw_temp_lower,
                'active_program_numeric': hw_program_numeric,
                'active_program_text': hw_program_text,
                'active_program_raw': hw_active_program,
                'switch_on_sensor_temp': hw_switch_on_sensor,
                'temp_target': hw_temp_target,
                'switch_off_sensor_temp': hw_switch_off_sensor,
                'pump_running': bool(hw_pump) if hw_pump is not None else None
            })
        
        return parsed
    
    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._authenticated = False