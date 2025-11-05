#!/usr/bin/env python3
"""
Debug-Script für Pellematic API
Zeigt alle verfügbaren Parameter und deren Werte an.
"""

import asyncio
import json
import logging
import sys
import os

# Einfacher Import für das aktuelle Verzeichnis
try:
    from custom_components.ofen.pellematic_api import PellematicAPI
except ImportError:
    # Fallback wenn Module nicht gefunden wird
    print("❌ Fehler: Kann pellematic_api Modul nicht importieren.")
    print("Stellen Sie sicher, dass Sie sich im richtigen Verzeichnis befinden.")
    sys.exit(1)

# Configure logging for debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def debug_all_data():
    """Holt alle verfügbaren Daten vom Pellematic System und zeigt sie an."""
    
    # REPLACE WITH YOUR ACTUAL CREDENTIALS!
    api = PellematicAPI(
        url="http://172.21.9.50",
        username="YOUR_USERNAME_HERE", 
        password="YOUR_PASSWORD_HERE",
        language="de",
        debug_mode=True  # DEBUG MODUS aktiviert!
    )
    
    try:
        print("🔍 DEBUG MODUS: Verbindung zum Pellematic System...")
        print("=" * 80)
        
        # Authentication testen
        auth_success = await api.authenticate()
        print(f"Authentifizierung: {'✅ Erfolgreich' if auth_success else '❌ Fehlgeschlagen'}")
        
        if not auth_success:
            return
        
        print(f"\n📊 Hole ALLE verfügbaren Parameter ({len(api.all_parameters)} Stück)...")
        print("=" * 80)
        
        # Alle Rohdaten holen
        raw_data = await api.fetch_data()
        if not raw_data:
            print("❌ Keine Daten erhalten!")
            return
        
        print(f"✅ {len(raw_data)} Parameter erfolgreich abgerufen!\n")
        
        # Parsed data mit Debug-Informationen
        parsed_data = await api.get_parsed_data()
        if parsed_data and parsed_data.get('debug_mode'):
            print("🔍 DEBUG DATEN ANALYSE:")
            print("-" * 80)
            
            # Kategorisiere die Parameter
            categories = {
                'Heizkreise (hk)': [],
                'Warmwasser (ww)': [],
                'Solarkreise (sk)': [],
                'Feuerungsautomaten (FA)': [],
                'Pufferspeicher (bestke)': [],
                'Pumpen (pu)': [],
                'System/Anlage': [],
                'Fernwartung': [],
                'Sonstige': []
            }
            
            for param, value in raw_data.items():
                if '.hk[' in param:
                    categories['Heizkreise (hk)'].append((param, value))
                elif '.ww[' in param:
                    categories['Warmwasser (ww)'].append((param, value))
                elif '.sk[' in param:
                    categories['Solarkreise (sk)'].append((param, value))
                elif 'FA[' in param:
                    categories['Feuerungsautomaten (FA)'].append((param, value))
                elif 'bestke' in param:
                    categories['Pufferspeicher (bestke)'].append((param, value))
                elif '.pu[' in param:
                    categories['Pumpen (pu)'].append((param, value))
                elif 'anlage' in param or 'betriebsart' in param:
                    categories['System/Anlage'].append((param, value))
                elif 'fernwartung' in param:
                    categories['Fernwartung'].append((param, value))
                else:
                    categories['Sonstige'].append((param, value))
            
            # Zeige kategorisierte Daten
            for category, items in categories.items():
                if items:
                    print(f"\n📂 {category} ({len(items)} Parameter):")
                    print("-" * 60)
                    for param, value in items:
                        # Zeige nur nicht-null Werte für bessere Übersicht
                        if value is not None and value != '':
                            print(f"  {param}: {value}")
            
            # Zeige wichtige Temperaturen extra
            print(f"\n🌡️ WICHTIGE TEMPERATUREN:")
            print("-" * 40)
            outside_temp = raw_data.get("CAPPL:LOCAL.L_aussentemperatur_ist")
            if outside_temp is not None:
                print(f"  Außentemperatur: {outside_temp}°C")
            
            buffer_temp = raw_data.get("CAPPL:LOCAL.L_bestke_temp_ist")
            if buffer_temp is not None:
                print(f"  Pufferspeicher: {buffer_temp}°C")
            
            for i in range(4):
                temp = raw_data.get(f"CAPPL:FA[{i}].L_kesseltemperatur")
                status = raw_data.get(f"CAPPL:FA[{i}].L_kesselstatus")
                if temp is not None:
                    print(f"  Kessel {i+1}: {temp}°C (Status: {status})")
            
            # Zeige Pumpen-Status
            print(f"\n🔄 PUMPEN STATUS:")
            print("-" * 30)
            for i in range(3):
                pump = raw_data.get(f"CAPPL:LOCAL.L_pu[{i}].pumpe")
                if pump is not None:
                    print(f"  Pumpe {i+1}: {'EIN' if pump else 'AUS'}")
            
            # Speichere Debug-Daten
            debug_filename = 'pellematic_debug_data.json'
            with open(debug_filename, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Alle Rohdaten gespeichert in: {debug_filename}")
            
            # Erstelle auch eine lesbare Version
            readable_filename = 'pellematic_debug_readable.txt'
            with open(readable_filename, 'w', encoding='utf-8') as f:
                f.write("PELLEMATIC DEBUG DATEN\n")
                f.write("=" * 50 + "\n\n")
                
                for category, items in categories.items():
                    if items:
                        f.write(f"{category} ({len(items)} Parameter):\n")
                        f.write("-" * 40 + "\n")
                        for param, value in items:
                            if value is not None and value != '':
                                f.write(f"  {param}: {value}\n")
                        f.write("\n")
            
            print(f"📄 Lesbare Version gespeichert in: {readable_filename}")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()

if __name__ == "__main__":
    print("🏠 Pellematic DEBUG TOOL")
    print("Analysiert alle verfügbaren Parameter vom ÖkOfen System")
    print("=" * 80)
    asyncio.run(debug_all_data())