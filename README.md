# StrangerCall

a single purpose honeypot to bait threat actors exploiting **callstranger**

emulated device: **LG Smart TV** (by default)

## INSTALL (manual)
1. (optional) rate limit the inbound UDP traffic with **iptables**:
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
- to evade possible SSDP DoS amplification on the running SSDP it rate limits the inbound requests per threat actor IP address
    - by defulat allows **1/sec**, **5/min**, **10/hour**
    - **rate limiting is optional, but ENABLED by default**

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