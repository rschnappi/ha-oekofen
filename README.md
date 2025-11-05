# ÖkOfen Pellematic Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/rschnappi/ha-oekofen.svg)](https://github.com/rschnappi/ha-oekofen/releases)
[![License](https://img.shields.io/github/license/rschnappi/ha-oekofen.svg)](LICENSE)

Eine benutzerdefinierte Home Assistant Integration für die Überwachung und Steuerung von ÖkOfen Pellematic Heizsystemen.

## Features

- **Multiple Temperature Sensors**: Outside temperature, buffer tank, and individual boiler temperatures
- **Boiler Status Monitoring**: Real-time status of heating boilers
- **Pump Status**: Monitor pump operation states
- **Error Monitoring**: Track system error count
- **Configuration Flow**: Easy setup through Home Assistant UI
- **Multi-language Support**: German and English interface
- **Configurable Update Intervals**: Set polling frequency (5-3600 seconds)

## Supported Sensors

### Temperature Sensors
- **Outside Temperature** - Current external temperature
- **Buffer Tank Temperature** - Storage tank temperature
- **Boiler Temperatures** - Individual boiler current and target temperatures

### Status Sensors  
- **Boiler Status** - Current operating status of each boiler
- **Error Count** - System error counter
- **Pump Status** - Operating state of circulation pumps

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install the "Ofen" integration
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration
5. Search for "Ofen" and follow the setup process

### Manual Installation

1. Copy the `custom_components/ofen` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Ofen" and follow the setup process

## Configuration

The integration can be configured through the Home Assistant UI:

1. Navigate to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Ofen**
4. Enter your ÖkOfen Pellematic details:
   - **URL**: Full URL of your system (e.g., http://172.21.9.50)
   - **Username**: Your login username
   - **Password**: Your login password  
   - **Language**: Interface language (de/en)
   - **Interval**: Update interval in seconds (5-3600 seconds, default: 30)

## Technical Details

This integration is based on analysis of the ÖkOfen Pellematic web interface and uses the same API endpoints that the official web interface uses. It performs the following steps:

1. **Authentication**: Logs in via the web interface using form-based authentication
2. **Session Management**: Maintains session cookies for subsequent requests
3. **Data Retrieval**: Fetches system parameters via JSON API calls
4. **Data Parsing**: Converts raw system data into Home Assistant entities

### API Parameters Retrieved

The integration fetches these key parameters from your system:
- `CAPPL:LOCAL.L_aussentemperatur_ist` - Outside temperature
- `CAPPL:FA[x].L_kesseltemperatur` - Boiler temperatures  
- `CAPPL:FA[x].L_kesselstatus` - Boiler status
- `CAPPL:LOCAL.L_bestke_temp_ist` - Buffer tank temperature
- `CAPPL:LOCAL.L_pu[x].pumpe` - Pump status
- `CAPPL:LOCAL.L_zaehler_fehler` - Error count

## Entities

Once configured, the integration will create the following entities:

### Sensors
- `sensor.outside_temperature` - Current outside temperature
- `sensor.buffer_tank_temperature` - Buffer tank temperature
- `sensor.boiler_1_temperature` - Boiler 1 current temperature
- `sensor.boiler_1_status` - Boiler 1 operating status
- `sensor.boiler_2_temperature` - Boiler 2 current temperature (if present)
- `sensor.boiler_2_status` - Boiler 2 operating status (if present)
- `sensor.error_count` - System error counter

### Switches (Read-only)
- `switch.pump_1` - Pump 1 status (monitoring only)
- `switch.pump_2` - Pump 2 status (monitoring only)  
- `switch.pump_3` - Pump 3 status (monitoring only)

> **Note**: Pump switches are read-only as pumps are controlled automatically by the heating system.

## Development

### File Structure

```
custom_components/ofen/
├── __init__.py          # Integration setup and entry points
├── manifest.json        # Integration metadata
├── const.py            # Constants and configuration
├── config_flow.py      # Configuration flow for UI setup
├── sensor.py           # Temperature sensor platform
└── switch.py           # Power switch platform
```

### Customization

To customize this integration for your specific oven:

1. **Update `const.py`**: Modify default values and add new configuration options
2. **Modify API calls**: Replace placeholder API calls in `sensor.py` and `switch.py` with actual device communication
3. **Add new platforms**: Create additional files for other entity types (climate, binary_sensor, etc.)

### API Integration

Currently, the integration uses placeholder data. To connect to a real device:

1. Install required dependencies in `manifest.json`
2. Implement actual API calls in the coordinator's `_async_update_data` method
3. Update switch methods to communicate with your device

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Home Assistant
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/yourusername/ofen/issues) page.