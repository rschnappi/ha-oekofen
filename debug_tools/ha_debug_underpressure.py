"""
Home Assistant Debug Script for ÖkOfen Underpressure Parameters
================================================================

Fügen Sie diesen Code in Home Assistant Developer Tools -> Template ein:

{{ states.sensor | selectattr('entity_id', 'match', '.*ofen.*') | list | length }}

Oder verwenden Sie diesen Service Call in Developer Tools -> Services:

Service: python_script.debug_underpressure
Data: {}

Speichern Sie diese Datei als: /config/python_scripts/debug_underpressure.py
"""

import asyncio
import json
import logging
from homeassistant.helpers import device_registry as dr, entity_registry as er

# Get the ÖkOfen integration
hass = hass  # Home Assistant instance
logger = logging.getLogger(__name__)

async def debug_ofen_parameters():
    """Debug ÖkOfen parameters in Home Assistant."""
    
    logger.info("🔍 Starting ÖkOfen parameter debug")
    
    # Find all ÖkOfen entities
    entity_registry = er.async_get(hass)
    ofen_entities = []
    
    for entity in entity_registry.entities.values():
        if entity.platform == "ofen" or "ofen" in entity.entity_id:
            ofen_entities.append(entity)
    
    logger.info(f"Found {len(ofen_entities)} ÖkOfen entities")
    
    # Look for underpressure related entities
    underpressure_entities = []
    for entity in ofen_entities:
        entity_id_lower = entity.entity_id.lower()
        if any(term in entity_id_lower for term in ['unterdruck', 'druck', 'pressure', 'vacuum', 'saugzug']):
            underpressure_entities.append(entity)
            logger.info(f"🎯 Underpressure entity found: {entity.entity_id}")
    
    # Get the coordinator data
    config_entries = hass.config_entries.async_entries("ofen")
    if config_entries:
        entry = config_entries[0]
        coordinator = hass.data.get("ofen", {}).get(entry.entry_id)
        
        if coordinator and hasattr(coordinator, 'data'):
            logger.info("📊 Checking coordinator data for underpressure parameters...")
            data = coordinator.data
            
            if isinstance(data, dict):
                underpressure_params = {}
                for key, value in data.items():
                    key_lower = key.lower()
                    if any(term in key_lower for term in ['unterdruck', 'druck', 'pressure', 'vacuum', 'saugzug']):
                        underpressure_params[key] = value
                        logger.info(f"✅ Found parameter: {key} = {value}")
                
                if underpressure_params:
                    logger.info(f"🎉 Found {len(underpressure_params)} underpressure parameters in coordinator data")
                    for key, value in underpressure_params.items():
                        logger.info(f"   {key}: {value}")
                else:
                    logger.warning("❌ No underpressure parameters found in coordinator data")
                    
                    # Log all available parameters for debugging
                    logger.info("📝 Available parameters in coordinator data:")
                    for key in sorted(data.keys()):
                        logger.info(f"   {key}")
            else:
                logger.warning("❌ Coordinator data is not a dictionary")
        else:
            logger.warning("❌ Could not access coordinator data")
    else:
        logger.warning("❌ No ÖkOfen config entries found")

# Run the debug
asyncio.create_task(debug_ofen_parameters())