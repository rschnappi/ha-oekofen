#!/usr/bin/env python3
"""
Quick connection test for debugging HA setup issues
"""

import asyncio
import logging
import sys
import os

# Einfacher Import für das aktuelle Verzeichnis
try:
    from custom_components.ofen.pellematic_api import PellematicAPI
except ImportError:
    print("❌ Fehler: Kann pellematic_api Modul nicht importieren.")
    sys.exit(1)

# Configure logging for debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_connection_simple():
    """Einfacher Verbindungstest."""
    
    print("🔧 HA Setup Debug Test")
    print("=" * 50)
    
    # Test mit echten Credentials (temporär für Debug)
    api = PellematicAPI(
        url="172.21.9.50",  # Nur IP wie in HA
        username="schnabl", 
        password="27071947",
        language="de",
        debug_mode=False  # Erstmal ohne Debug
    )
    
    try:
        print("1️⃣ Teste URL-Verarbeitung...")
        print(f"   Eingegebene URL: 172.21.9.50")
        print(f"   Verarbeitete URL: {api.url}")
        
        print("\n2️⃣ Teste Authentifizierung...")
        auth_success = await api.authenticate()
        print(f"   Authentifizierung: {'✅ Erfolgreich' if auth_success else '❌ Fehlgeschlagen'}")
        
        if not auth_success:
            print("\n🔍 Mögliche Ursachen:")
            print("   - Falsche IP-Adresse oder Port")
            print("   - Pellematic System nicht erreichbar")
            print("   - Falsche Credentials")
            print("   - Firewall blockiert Verbindung")
            return
        
        print("\n3️⃣ Teste Datenabruf...")
        data = await api.fetch_data()
        if data:
            print(f"   ✅ Daten erhalten: {len(data)} Parameter")
            print(f"   Beispiel: Außentemperatur = {data.get('CAPPL:LOCAL.L_aussentemperatur_ist')}")
        else:
            print("   ❌ Keine Daten erhalten")
        
        print("\n4️⃣ Teste geparsete Daten...")
        parsed = await api.get_parsed_data()
        if parsed:
            print(f"   ✅ Geparste Daten erhalten")
            print(f"   Außentemperatur: {parsed.get('outside_temperature')}")
            print(f"   Pufferspeicher: {parsed.get('buffer_tank_temperature')}")
            print(f"   Kessel gefunden: {len(parsed.get('boilers', []))}")
        
    except Exception as e:
        print(f"\n❌ Verbindungsfehler: {e}")
        print("\n🔍 Debug-Informationen:")
        print(f"   URL: {api.url}")
        print(f"   Username: {api.username}")
        print(f"   Session erstellt: {api._session is not None}")
        
        import traceback
        print("\n📋 Vollständiger Fehler:")
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(test_connection_simple())