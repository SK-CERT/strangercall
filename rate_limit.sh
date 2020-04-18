#!/bin/bash
# OBJECTIVE: rate limit the SSDP inboud traffic to evade SSDP DDoS amplification attack
# add this to your initialization iptables script

#iptables -F
#iptables -X

iptables -N SSDP_RATE_LIMIT
	iptables -A SSDP_RATE_LIMIT -m hashlimit --hashlimit-above 5/minute --hashlimit-mode srcip --hashlimit-name ssdp_rate_limit -j DROP
	iptables -A SSDP_RATE_LIMIT -m hashlimit --hashlimit-above 10/hour --hashlimit-mode srcip --hashlimit-name ssdp_rate_limit -j DROP
	iptables -A SSDP_RATE_LIMIT -j ACCEPT
# optionally jump to your custom LOG_DROP or LOG_ACCEPT chains

# SSDP honeypot
iptables -I INPUT -p udp --dport 1900 -j SSDP_RATE_LIMIT

# UPNP honeypot
iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
iptables -I INPUT -p tcp --dport 1784 -j ACCEPT