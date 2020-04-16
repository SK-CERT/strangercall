# UPnP honeypot

a single purpose honeypot to bait threat actors exploiting **callstranger**

emulated device: **LG Smart TV**

## INSTALL
1. `pip install -r requires.txt`
2. rate limit the outbound UDP traffic with **iptables**:
    ```bash
    iptables -N SSDP_NOTIFY_RATE_LIMIT
    
    iptables -I OUTPUT -p udp -s <MY_IP> -j SSDP_NOTIFY_RATE_LIMIT
    iptables -A SSDP_NOTIFY_RATE_LIMIT -m limit --limit 5/minute -j ACCEPT
    iptables -A SSDP_NOTIFY_RATE_LIMIT -m limit --limit 10/hour -j ACCEPT
    iptables -A SSDP_NOTIFY_RATE_LIMIT -j DROP
    ```
3. configure the honeypot in `config.ini`
4. edit the `eventSubURL` elements in `description.xml`

## Structure
### hon_ssdp.py
- UDP/1900 socket listener
- replies to `M-SEARCH` requests
- rate limits the outbound traffic

**USAGE**: `python3 hon_ssdp.py`

### hon_description_webserber.py
- TCP/5000 HTTP server
- returns the services description XML file 

**USAGE**: `python3 hon_description_webserver.py`

### hon_upnp.py 
- TCP/5000 socket listener
- accepts connections
- receives SUBSCRIBE requests

**USAGE**: `python3 hon_upnp.py`

### upnp_sniff.py
- TCP/5000 request sniffer
- logs the incoming requests

**USAGE**: `python3 upnp_sniff.py`

### services.py
- helper file to craft NOTIFY request bodies