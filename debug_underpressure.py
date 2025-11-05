#!/usr/bin/env python3
"""Debug script to find underpressure parameters on ÖkOfen Pellematic system."""

import asyncio
import json
import sys
from custom_components.ofen.pellematic_api import PellematicAPI

async def debug_underpressure_parameters():
    """Debug underpressure parameters availability."""
    
    # Configure your connection here
    HOST = "172.21.9.50"  # Your Pellematic IP
    USERNAME = "admin"    # Your username
    PASSWORD = "password" # Your password
    
    print("🔍 ÖkOfen Pellematic Underpressure Parameter Debug")
    print("=" * 60)
    
    # Create API instance with debug mode
    api = PellematicAPI(f"http://{HOST}", USERNAME, PASSWORD, debug_mode=True)
    
    try:
        print("🔐 Authenticating...")
        if not await api.authenticate():
            print("❌ Authentication failed!")
            return
        print("✅ Authentication successful!")
        
        print("\n🔍 Testing underpressure parameter variations...")
        
        # Test different underpressure parameter names
        underpressure_candidates = [
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
            # Try variations without FA[0]
            "CAPPL:LOCAL.unterdruck_modus",
            "CAPPL:LOCAL.L_unterdruck",
            # Try different indices
            "CAPPL:FA[1].unterdruck_modus",
            "CAPPL:FA[1].L_unterdruck",
        ]
        
        session = await api._get_session()
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'de',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'http://{HOST}/',
            'Origin': f'http://{HOST}'
        }
        
        # Test each parameter individually
        found_parameters = []
        for param in underpressure_candidates:
            try:
                async with session.post(
                    f"http://{HOST}/?action=get&attr=1",
                    data=json.dumps([param]),
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0 and data[0] is not None:
                            result = data[0]
                            if isinstance(result, dict) and 'value' in result:
                                value = result['value']
                                print(f"✅ FOUND: {param} = {value}")
                                if result.get('shortText'):
                                    print(f"   📝 Description: {result['shortText']}")
                                if result.get('unitText'):
                                    print(f"   📏 Unit: {result['unitText']}")
                                found_parameters.append({
                                    'parameter': param,
                                    'value': value,
                                    'full_response': result
                                })
                            else:
                                print(f"❌ {param}: No value in response")
                        else:
                            print(f"❌ {param}: Empty or null response")
                    else:
                        print(f"❌ {param}: HTTP {response.status}")
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"❌ {param}: Error - {e}")
        
        print(f"\n📊 Summary: Found {len(found_parameters)} underpressure-related parameters")
        
        if found_parameters:
            print("\n🎯 Found Parameters Details:")
            for param_data in found_parameters:
                print(f"\nParameter: {param_data['parameter']}")
                print(f"Value: {param_data['value']}")
                print(f"Full Response: {json.dumps(param_data['full_response'], indent=2)}")
        
        # Also try to get a broader range of FA[0] parameters to see what's available
        print("\n🔍 Scanning all FA[0] parameters for underpressure-related terms...")
        
        # Get all FA[0] parameters
        fa_params = [p for p in api.all_parameters if "FA[0]" in p]
        print(f"Found {len(fa_params)} FA[0] parameters in all_parameters list")
        
        # Test them in small batches
        batch_size = 10
        for i in range(0, len(fa_params), batch_size):
            batch = fa_params[i:i+batch_size]
            try:
                async with session.post(
                    f"http://{HOST}/?action=get&attr=1",
                    data=json.dumps(batch),
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for j, param in enumerate(batch):
                            if j < len(data) and data[j] is not None:
                                result = data[j]
                                if isinstance(result, dict) and 'value' in result:
                                    # Check if this parameter might be related to underpressure
                                    param_lower = param.lower()
                                    if any(term in param_lower for term in ['unterdruck', 'druck', 'vacuum', 'saugzug']):
                                        print(f"🔍 POTENTIAL: {param} = {result['value']}")
                                        if result.get('shortText'):
                                            print(f"   📝 Description: {result['shortText']}")
                await asyncio.sleep(0.2)
            except Exception as e:
                print(f"❌ Batch {i}-{i+batch_size}: Error - {e}")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await api.close()
        print("\n🔌 Connection closed")

if __name__ == "__main__":
    asyncio.run(debug_underpressure_parameters())