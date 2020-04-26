# StrangerCall

a single purpose honeypot to bait threat actors exploiting **callstranger**

emulated device: **LG Smart TV** (by default)

## INSTALL (manual)
1. rate limit the inbound UDP traffic with **iptables**:
    - view and optionally edit port numbers for UPNP honeypot
    - run `bash rate_limit.sh`
2. configure the honeypot in `config.ini` (rename or copy the default config from [config example](config.ini.example))
3. inspect and rename the description XML [file](description.xml.example) to `description.xml`
4. inspect and edit the `eventSubURL` elements in the XML if necessary
    - [if changed] don't forget the change the UPNP port in the configuration file
5. create python virtual environment
6. `pip install .`

## Structure
### hon_ssdp.py
- UDP/1900 socket listener
- replies to `M-SEARCH` requests with arbitrary `ST` header
- (TODO) rate limits the outbound traffic

**USAGE**: `hon_ssdp`

### hon_upnp.py 
- TCP/1784 socket listener
- accepts connections
- receives SUBSCRIBE requests
- optionally responses with standard HTTP 200 OK or doesn't (configurable)

**USAGE**: `hon_upnp`

### upnp_sniff.py
- TCP/1784 sniffer
- logs the inbound/outbound traffic

**USAGE**: `upnp_sniff`

### services.py
- helper file to craft NOTIFY request body