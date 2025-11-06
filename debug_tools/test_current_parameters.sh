#!/bin/bash
# Test current parameter request from user

echo "=== Testing current parameter request ==="
curl 'http://172.21.9.50/?action=get&attr=1' \
  -H 'Accept: application/json, text/javascript, */*; q=0.01' \
  -H 'Accept-Language: de' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -b 'language=de; pksession=98913' \
  -H 'DNT: 1' \
  -H 'Origin: http://172.21.9.50' \
  -H 'Referer: http://172.21.9.50/' \
  -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0' \
  -H 'X-Requested-With: XMLHttpRequest' \
  --data-raw '["CAPPL:FA[0].asche_minimum_laufzeit_asche","CAPPL:FA[0].asche_aschedauer","CAPPL:FA[0].asche_nachlaufzeit_aschebox","CAPPL:FA[0].L_kesselstatus","CAPPL:FA[0].L_kesseltemperatur","CAPPL:FA[0].L_kesseltemperatur_soll_anzeige","CAPPL:FA[0].L_drehzahl_ascheschnecke_ist","CAPPL:LOCAL.L_fernwartung_datum_zeit_sek","CAPPL:LOCAL.L_zaehler_fehler"]' \
  --insecure

echo -e "\n\n=== Current parameters in this request ==="
echo "CAPPL:FA[0].asche_minimum_laufzeit_asche"
echo "CAPPL:FA[0].asche_aschedauer" 
echo "CAPPL:FA[0].asche_nachlaufzeit_aschebox"
echo "CAPPL:FA[0].L_kesselstatus"
echo "CAPPL:FA[0].L_kesseltemperatur"
echo "CAPPL:FA[0].L_kesseltemperatur_soll_anzeige"
echo "CAPPL:FA[0].L_drehzahl_ascheschnecke_ist"
echo "CAPPL:LOCAL.L_fernwartung_datum_zeit_sek"
echo "CAPPL:LOCAL.L_zaehler_fehler"