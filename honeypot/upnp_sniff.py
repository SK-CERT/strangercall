#!/usr/bin/env python3
#
# simple scapy-based sniffer for TCP UPnP requests
# log message format: "FROM ip:port TO ip:port UTF-8 headers"
#
# usage:
#    python3 upnp_sniff.py

import configparser
import logging
from scapy.sendrecv import sniff
from scapy.sessions import IPSession
from scapy.layers.l2 import Ether
from scapy.layers.inet import TCP, IP
from scapy.packet import Raw
from sys import stdout

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
config = config_parser['sniffer']

### CONFIG VARS ###
_LOG_LEVEL = config_parser['global'].get('log_level', fallback='info').upper()
_SNIFFER_IFACE = config.get('iface')
_SNIFFER_TCP_PORT = config_parser['upnp'].getint('port', fallback=1784)
_SNIFFER_FILTER = f'tcp port {_SNIFFER_TCP_PORT}'

# intialize logger
log = logging.getLogger('upnp_sniff')
log.setLevel(_LOG_LEVEL)
formatter = logging.Formatter('%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(stream=stdout)
handler.setFormatter(formatter)
log.addHandler(handler)


# packet inspection callback
def inspect_packet(pkt: Ether):
    ip = pkt[IP]
    tcp = pkt[IP][TCP]
    log.info(f'FROM {ip.src}:{tcp.sport} TO {ip.dst}:{tcp.dport} {len(tcp.payload.load)} bytes - {tcp.payload.load}')


def main():
    # starts an infinite sniffer loop with the following properties
    #   the IP packets are deframented on-the-flow
    #   sniffer is filtered for the specified TCP/5000 and for scapy dependent filer to contain the Raw layer (DATA)
    #   capture packet on iface, do not store the traffic and resolve each packet with specified callback
    sniff(session=IPSession,
          filter=_SNIFFER_FILTER,
          lfilter=lambda x: x.haslayer(Raw),
          iface=_SNIFFER_IFACE,
          prn=inspect_packet,
          store=False)


if __name__ == '__main__':
    log.info(f'Started UPnP sniffer filter: "{_SNIFFER_FILTER}" on {_SNIFFER_IFACE}')
    main()
