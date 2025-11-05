#!/usr/bin/env python3
"""
Improved Pellematic Data Fetcher
Fixed version based on login page analysis.
"""

import requests
import json
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration - REPLACE WITH YOUR CREDENTIALS!
PELLEMATIC_IP = "172.21.9.50"
USERNAME = "YOUR_USERNAME_HERE"
PASSWORD = "YOUR_PASSWORD_HERE"

def fetch_pellematic_data():
    """Fetch data from Pellematic heating system."""
    
    session = requests.Session()
    session.verify = False
    
    # Step 1: Get the login page first to set up session
    print("Getting login page...")
    try:
        main_page = session.get(f"http://{PELLEMATIC_IP}/", timeout=10)
        main_page.raise_for_status()
        print(f"✅ Got login page, cookies: {dict(session.cookies)}")
    except Exception as e:
        print(f"❌ Failed to get login page: {e}")
        return None
    
    # Step 2: Login
    print("Logging in...")
    login_url = f"http://{PELLEMATIC_IP}/index.cgi"
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'language': 'de',
        'submit': 'Anmelden'
    }
    
    # Add headers that match browser behavior
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': f'http://{PELLEMATIC_IP}',
        'Referer': f'http://{PELLEMATIC_IP}/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        login_response = session.post(login_url, data=login_data, headers=headers, timeout=10, allow_redirects=True)
        login_response.raise_for_status()
        
        print(f"✅ Login response status: {login_response.status_code}")
        print(f"🍪 Cookies after login: {dict(session.cookies)}")
        
        # Check for login error cookie
        if 'LoginError' in session.cookies:
            print(f"❌ Login error detected: {session.cookies['LoginError']}")
            return None
        
        # Check if we have a session cookie (might be named differently)
        session_cookies = [cookie for cookie in session.cookies.keys() if 'session' in cookie.lower() or 'pk' in cookie.lower()]
        if session_cookies:
            print(f"✅ Found session cookies: {session_cookies}")
        else:
            print("⚠️  No obvious session cookie found, but continuing...")
        
        # Check if we were redirected to a different page (successful login)
        if login_response.url != login_url:
            print(f"✅ Redirected to: {login_response.url}")
        
        # Save login response for debugging
        with open('/homeassistant/pellematic/login_response.html', 'w', encoding='utf-8') as f:
            f.write(login_response.text)
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None
    
    # Step 3: Get data
    print("Fetching system data...")
    data_url = f"http://{PELLEMATIC_IP}/?action=get&attr=1"
    
    # All parameters from the original curl command
    parameters = [
        "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek","CAPPL:LOCAL.heizkreisregler_vorhanden[0]","CAPPL:LOCAL.heizkreisregler_vorhanden[1]","CAPPL:LOCAL.heizkreisregler_vorhanden[2]","CAPPL:LOCAL.anlage_betriebsart","CAPPL:LOCAL.hk[0].vorhanden","CAPPL:LOCAL.hk[0].betriebsart[0]","CAPPL:LOCAL.hk[1].vorhanden","CAPPL:LOCAL.hk[1].betriebsart[0]","CAPPL:LOCAL.hk[2].vorhanden","CAPPL:LOCAL.hk[2].betriebsart[0]","CAPPL:LOCAL.hk[3].vorhanden","CAPPL:LOCAL.hk[3].betriebsart[0]","CAPPL:LOCAL.hk[4].vorhanden","CAPPL:LOCAL.hk[4].betriebsart[0]","CAPPL:LOCAL.hk[5].vorhanden","CAPPL:LOCAL.hk[5].betriebsart[0]","CAPPL:LOCAL.hk[0].betriebsart[1]","CAPPL:LOCAL.hk[1].betriebsart[1]","CAPPL:LOCAL.hk[2].betriebsart[1]","CAPPL:LOCAL.hk[3].betriebsart[1]","CAPPL:LOCAL.hk[4].betriebsart[1]","CAPPL:LOCAL.hk[5].betriebsart[1]","CAPPL:LOCAL.hk[0].betriebsart[2]","CAPPL:LOCAL.hk[1].betriebsart[2]","CAPPL:LOCAL.hk[2].betriebsart[2]","CAPPL:LOCAL.hk[3].betriebsart[2]","CAPPL:LOCAL.hk[4].betriebsart[2]","CAPPL:LOCAL.hk[5].betriebsart[2]","CAPPL:LOCAL.ww[0].vorhanden","CAPPL:LOCAL.ww[0].betriebsart[0]","CAPPL:LOCAL.ww[1].vorhanden","CAPPL:LOCAL.ww[1].betriebsart[0]","CAPPL:LOCAL.ww[2].vorhanden","CAPPL:LOCAL.ww[2].betriebsart[0]","CAPPL:LOCAL.ww[0].betriebsart[1]","CAPPL:LOCAL.ww[1].betriebsart[1]","CAPPL:LOCAL.ww[2].betriebsart[1]","CAPPL:LOCAL.ww[0].betriebsart[2]","CAPPL:LOCAL.ww[1].betriebsart[2]","CAPPL:LOCAL.ww[2].betriebsart[2]","CAPPL:LOCAL.sk[0].vorhanden","CAPPL:LOCAL.sk[0].betriebsart","CAPPL:LOCAL.sk[2].vorhanden","CAPPL:LOCAL.sk[2].betriebsart","CAPPL:LOCAL.sk[4].vorhanden","CAPPL:LOCAL.sk[4].betriebsart","CAPPL:LOCAL.sk[1].vorhanden","CAPPL:LOCAL.sk[1].betriebsart","CAPPL:LOCAL.sk[3].vorhanden","CAPPL:LOCAL.sk[3].betriebsart","CAPPL:LOCAL.sk[5].vorhanden","CAPPL:LOCAL.sk[5].betriebsart","CAPPL:LOCAL.pellematic_vorhanden[0]","CAPPL:FA[0].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[1]","CAPPL:FA[1].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[2]","CAPPL:FA[2].betriebsart_fa","CAPPL:LOCAL.pellematic_vorhanden[3]","CAPPL:FA[3].betriebsart_fa","CAPPL:LOCAL.fernwartung_einheit","CAPPL:LOCAL.L_aussentemperatur_ist","CAPPL:FA[0].L_kesselstatus","CAPPL:FA[1].L_kesselstatus","CAPPL:FA[2].L_kesselstatus","CAPPL:FA[3].L_kesselstatus","CAPPL:FA[0].L_kesseltemperatur","CAPPL:FA[0].L_kesseltemperatur_soll_anzeige","CAPPL:FA[1].L_kesseltemperatur","CAPPL:FA[1].L_kesseltemperatur_soll_anzeige","CAPPL:FA[2].L_kesseltemperatur","CAPPL:FA[2].L_kesseltemperatur_soll_anzeige","CAPPL:FA[3].L_kesseltemperatur","CAPPL:FA[3].L_kesseltemperatur_soll_anzeige","CAPPL:LOCAL.bestke_vorhanden","CAPPL:LOCAL.L_bestke_temp_ist","CAPPL:LOCAL.L_bestke_umschaltventil","CAPPL:LOCAL.pu[0].vorhanden","CAPPL:LOCAL.L_pu[0].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[0].einschaltfuehler_soll","CAPPL:LOCAL.pu[1].vorhanden","CAPPL:LOCAL.L_pu[1].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[1].einschaltfuehler_soll","CAPPL:LOCAL.pu[2].vorhanden","CAPPL:LOCAL.L_pu[2].einschaltfuehler_ist","CAPPL:LOCAL.L_pu[2].einschaltfuehler_soll","CAPPL:LOCAL.L_pu[0].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[0].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[1].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[1].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[2].ausschaltfuehler_ist","CAPPL:LOCAL.L_pu[2].ausschaltfuehler_soll","CAPPL:LOCAL.L_pu[0].pumpe","CAPPL:LOCAL.L_pu[1].pumpe","CAPPL:LOCAL.L_pu[2].pumpe","CAPPL:LOCAL.L_zaehler_fehler"
    ]
    
    data_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'de',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'http://{PELLEMATIC_IP}/',
        'Origin': f'http://{PELLEMATIC_IP}'
    }
    
    try:
        response = session.post(
            data_url,
            data=json.dumps(parameters),
            headers=data_headers,
            timeout=10
        )
        
        print(f"📊 Data response status: {response.status_code}")
        
        if response.status_code == 403:
            print("❌ Access forbidden - login might have failed")
            # Try to check current page to see login status
            current_page = session.get(f"http://{PELLEMATIC_IP}/", timeout=5)
            if 'login' in current_page.text.lower():
                print("❌ Still on login page - authentication failed")
            return None
            
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Retrieved {len(data)} data points")
        
        # Create mapping of parameters to values
        result = {}
        for i, param in enumerate(parameters):
            if i < len(data):
                result[param] = data[i]
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print(f"Response content: {response.text[:200] if 'response' in locals() else 'No response'}")
        return None

def print_key_values(data):
    """Print some key system values."""
    if not data:
        return
    
    print("\n🔥 Key System Values:")
    print("-" * 50)
    
    # Outside temperature
    outside_temp = data.get("CAPPL:LOCAL.L_aussentemperatur_ist")
    if outside_temp is not None:
        print(f"Outside Temperature: {outside_temp}°C")
    
    # Boiler temperatures and status
    for i in range(4):
        status = data.get(f"CAPPL:FA[{i}].L_kesselstatus")
        temp = data.get(f"CAPPL:FA[{i}].L_kesseltemperatur")
        temp_soll = data.get(f"CAPPL:FA[{i}].L_kesseltemperatur_soll_anzeige")
        
        if status is not None:
            print(f"Boiler {i+1} Status: {status}")
        if temp is not None:
            print(f"Boiler {i+1} Temperature: {temp}°C" + (f" (Target: {temp_soll}°C)" if temp_soll else ""))
    
    # Buffer tank
    buffer_temp = data.get("CAPPL:LOCAL.L_bestke_temp_ist")
    if buffer_temp is not None:
        print(f"Buffer Tank Temperature: {buffer_temp}°C")
    
    # Pump status
    for i in range(3):
        pump = data.get(f"CAPPL:LOCAL.L_pu[{i}].pumpe")
        if pump is not None:
            print(f"Pump {i+1}: {'ON' if pump else 'OFF'}")
    
    # Error count
    errors = data.get("CAPPL:LOCAL.L_zaehler_fehler")
    if errors is not None:
        print(f"Error Count: {errors}")

if __name__ == "__main__":
    print("🏠 Pellematic Heating System Data Fetcher v2")
    print("=" * 50)
    
    data = fetch_pellematic_data()
    
    if data:
        # Save full data
        with open('/homeassistant/pellematic/pellematic_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Full data saved to pellematic_data.json")
        
        # Print key values
        print_key_values(data)
        
        # Print all parameter names for reference
        print(f"\n📊 All Parameters ({len(data)} total):")
        print("-" * 50)
        for param, value in data.items():
            print(f"{param}: {value}")
    
    else:
        print("❌ Failed to retrieve data")