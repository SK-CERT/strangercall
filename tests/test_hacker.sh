#!/bin/bash

curl --no-keepalive --connect-timeout 10 -v -X SUBSCRIBE -H "NT: upnp:event" -H "TIMEOUT: Second-180" -H "CALLBACK: <http://10.0.0.1>" "$1"
echo "$(date)" "sent."