# ÖkOfen Home Assistant Integration

## Project Overview
This is a custom Home Assistant integration for ÖkOfen Pellematic heating systems, specifically optimized for the Pellematic 2012 model based on extensive real-world testing and analysis.

## Key Technical Insights (From Direct Server Analysis)
- **Critical**: ÖkOfen requires `Content-Type: application/json` headers for all API requests
- **Authentication**: Uses index.cgi endpoint with form-based login
- **Data Retrieval**: `/?action=get&attr=1` endpoint with POST requests
- **Session Management**: Cookie-based with pksession parameter
- **Web Interface**: jQuery-based with 5-second AJAX polling intervals
- **Headers**: Must include User-Agent and XMLHttpRequest headers for compatibility

## Proven Working Configuration
Based on successful curl testing:
```bash
# Login
curl -X POST "/index.cgi" -d "user=<username>&pass=<password>&submit=Anmelden"

# Data retrieval  
curl -X POST "/?action=get&attr=1" -H "Content-Type: application/json" -d '["CAPPL:LOCAL.L_aussentemperatur_ist"]'
```

## Project Structure
```
custom_components/oekofen/
├── __init__.py          # Integration initialization
├── manifest.json        # Integration metadata
├── config_flow.py       # Configuration UI
├── sensor.py           # Sensor entities
└── pellematic_api.py   # API client with verified headers
```

## Development Guidelines
- Always use `Content-Type: application/json` for API requests
- Include proper User-Agent headers for compatibility
- Implement robust session management with cookie handling
- Use async/await patterns for all HTTP requests
- Include comprehensive error handling and logging
- Follow Home Assistant integration best practices

## Version Information
Starting fresh with v0.0.1 incorporating all discovered insights and proven working configurations.