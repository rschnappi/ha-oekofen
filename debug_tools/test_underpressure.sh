#!/bin/bash

# Test script to check for underpressure parameters
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
  --data-raw '["CAPPL:FA[0].unterdruck_modus","CAPPL:FA[0].L_unterdruck"]' \
  --insecure