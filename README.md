# StrangerCall

a single purpose honeypot to bait threat actors exploiting **callstranger**

emulated device: **LG Smart TV** (by default)

## INSTALL (manual)
1. `pip install -r requires.txt`
2. rate limit the inbound UDP traffic with **iptables**:
    - view and optionally edit port numbers for UPNP honeypot
    - run `bash rate_limit.sh`
3. configure the honeypot in `config.ini` (rename or copy the default config from [config example](config.ini.example))
4. inspect and rename the description XML [file](description.xml.example) to `description.xml`
5. inspect and edit the `eventSubURL` elements in the XML if necessary
    - [if changed] don't forget the change the UPNP port in the configuration file 

## Structure
### hon_ssdp.py
- UDP/1900 socket listener
- replies to `M-SEARCH` requests with arbitrary `ST` header
- (TODO) rate limits the outbound traffic

**USAGE**: `python3 honeypot/hon_ssdp.py`

### hon_description_webserber.py
- TCP/5000 HTTP server
- returns the services description XML file

**USAGE**: `python3 honeypot/hon_description_webserver.py`

### hon_upnp.py 
- TCP/1784 socket listener
- accepts connections
- receives SUBSCRIBE requests
- optionally responses with standard HTTP 200 OK or doesn't (configurable)

**USAGE**: `python3 hon_upnp.py`

### upnp_sniff.py
- TCP/1784 sniffer
- logs the inbound/outbound traffic

**USAGE**: `python3 honeypot/upnp_sniff.py`

### services.py
- helper file to craft NOTIFY request body