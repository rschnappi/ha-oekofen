# Home Assistant Developer Tools Debug Commands für ÖkOfen Unterdruck-Parameter
# =====================================================================================

# 1. TEMPLATE TEST - Fügen Sie das in Developer Tools -> Template ein:
# =====================================================================================

# Zeige alle ÖkOfen Entities:
{{ states | selectattr('entity_id', 'match', '.*ofen.*') | map(attribute='entity_id') | list }}

# Suche nach Unterdruck-bezogenen Entities:
{{ states | selectattr('entity_id', 'match', '.*(unterdruck|druck|pressure|vacuum|saugzug).*') | map(attribute='entity_id') | list }}

# Zeige alle ÖkOfen Attribute:
{% for state in states if 'ofen' in state.entity_id %}
{{ state.entity_id }}: {{ state.state }} ({{ state.attributes }})
{% endfor %}

# =====================================================================================
# 2. SERVICE CALL TEST - Fügen Sie das in Developer Tools -> Services ein:
# =====================================================================================

# Service: homeassistant.reload_config_entry
# Target:
#   entity_id: 
#     - sensor.ofen_boiler_0_status  # (ersetzen Sie mit Ihrer ÖkOfen Entity)

# =====================================================================================
# 3. LOGBOOK CHECK - Suchen Sie in Settings -> System -> Logs nach:
# =====================================================================================
# - "ofen"
# - "unterdruck" 
# - "Missing/unavailable parameters"
# - "Parameter group pre-load failed"

# =====================================================================================
# 4. MANUAL API TEST - Terminal Befehle (falls Sie Zugang haben):
# =====================================================================================

curl 'http://172.21.9.50/?action=get&attr=1' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Accept-Language: de' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -b 'language=de; pksession=IHRE_SESSION_ID' \
  -H 'DNT: 1' \
  -H 'Origin: http://172.21.9.50' \
  -H 'Referer: http://172.21.9.50/' \
  -H 'User-Agent: Mozilla/5.0' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --data-raw '["CAPPL:FA[0].unterdruck_modus","CAPPL:FA[0].L_unterdruck"]' \
  --insecure

# =====================================================================================
# 5. HOME ASSISTANT ENTITY INFORMATION
# =====================================================================================

# Schauen Sie in Settings -> Devices & Services -> ÖkOfen Integration
# und prüfen Sie welche Entities tatsächlich erstellt wurden.

# =====================================================================================
# ERWARTETE ENTITIES (falls Unterdruck-Parameter funktionieren):
# =====================================================================================
# - sensor.ofen_underpressure_mode
# - sensor.ofen_underpressure_value  
# - sensor.ofen_fan_speed
# - sensor.ofen_suction_fan_speed