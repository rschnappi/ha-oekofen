# ÖkOfen Home Assistant Integration

## Project Overview
This is a custom Home Assistant integration for ÖkOfen Pellematic heating systems, specifically optimized for the Pellematic 2012 model based on extensive real-world testing and analysis.

## VERIFIED Working Configuration (Nov 2025 - Real Device Testing)

### Authentication (TESTED ✓)
```bash
curl -i -c cookies.txt "http://IP/index.cgi" \
  -d "username=USER&password=PASS&language=de&submit=Anmelden"
```
- **Method**: POST to `/index.cgi`
- **Content-Type**: `application/x-www-form-urlencoded`
- **Fields**: `username`, `password`, `language`, `submit`
- **Success**: HTTP 303 + `Set-Cookie: pksession=XXXXX` + `LoginError=0`
- **Important**: Newer firmware uses `username`/`password` (NOT `user`/`pass`)

### Data Retrieval (TESTED ✓)
```bash
curl -b cookies.txt -X POST "http://IP/?action=get&attr=1" \
  -H "Content-Type: application/json" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d '["CAPPL:LOCAL.L_aussentemperatur_ist"]'
```
- **Method**: POST to `/?action=get&attr=1`
- **Content-Type**: `application/json`
- **Body**: JSON array of parameter names
- **Cookie**: Session cookie from login required
- **Header**: `X-Requested-With: XMLHttpRequest` required

### Key Insights
- Session timeout: 600 seconds (10 minutes)
- Unauthenticated requests redirect to `/login.cgi`
- Login page shows correct field names in HTML form

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