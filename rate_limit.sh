#!/bin/bash

# ensure a chain exists and its empty
# iptables -N SSDP_LOG_DROP
iptables -F SSDP_LOG_DROP
iptables -A SSDP_LOG_DROP -m limit --limit 5/minute -j LOG --log-ip-options --log-tcp-options --log-uid --log-prefix "SSDP-REQUEST-DROP " --log-level info
iptables -A SSDP_LOG_DROP -m limit --limit 10/hour -j LOG --log-ip-options --log-tcp-options --log-uid --log-prefix "SSDP-REQUEST-DROP " --log-level info
iptables -A SSDP_LOG_DROP -j DROP

# iptables -I INPUT -m hashlimit -p udp --dport 1900 --hashlimit-above 3/second --hashlimit-mode srcip --hashlimit-name ssdp_per_second -j SSDP_LOG_DROP