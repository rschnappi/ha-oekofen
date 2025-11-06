"""Test script to validate Pellematic API connection."""
import asyncio
import logging
from pellematic_api import PellematicAPI

# Configure logging
logging.basicConfig(level=logging.DEBUG)

async def test_connection():
    """Test the API connection."""
    # REPLACE WITH YOUR ACTUAL CREDENTIALS!
    api = PellematicAPI(
        url="172.21.9.50",  # Just IP - http:// will be added automatically
        username="YOUR_USERNAME_HERE", 
        password="YOUR_PASSWORD_HERE",
        language="de"
    )
    
    try:
        print("Testing authentication...")
        auth_success = await api.authenticate()
        print(f"Authentication: {'✅ Success' if auth_success else '❌ Failed'}")
        
        if auth_success:
            print("\nFetching raw data...")
            raw_data = await api.fetch_data()
            if raw_data:
                print(f"✅ Retrieved {len(raw_data)} raw parameters")
                
                print("\nFetching parsed data...")
                parsed_data = await api.get_parsed_data()
                if parsed_data:
                    print("✅ Parsed data:")
                    print(f"  Outside Temperature: {parsed_data.get('outside_temperature')}°C")
                    print(f"  Buffer Tank: {parsed_data.get('buffer_tank_temperature')}°C")
                    print(f"  Error Count: {parsed_data.get('error_count')}")
                    print(f"  Boilers: {len(parsed_data.get('boilers', []))}")
                    print(f"  Pumps: {len(parsed_data.get('pumps', []))}")
                    
                    for boiler in parsed_data.get('boilers', []):
                        print(f"  Boiler {boiler['index'] + 1}: {boiler['temperature']}°C (Status: {boiler['status']})")
                    
                    for pump in parsed_data.get('pumps', []):
                        print(f"  Pump {pump['index'] + 1}: {'ON' if pump['running'] else 'OFF'}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await api.close()

if __name__ == "__main__":
    asyncio.run(test_connection())