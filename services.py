#!/usr/bin/env python3
#
# helper file for crafting 'HTTP 200 OK' response

import configparser
from datetime import datetime
from tzlocal import get_localzone

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
config = config_parser['ssdp_services']

_UUID = config.get('uuid')
_SERVER = config.get('server_header')
_CACHE_CONTROL = config.get('cache-control_header', fallback='max-age=1800')
_ADDITIONAL_HEADERS_LIST = config.get('header_tail', fallback='').split('\r\n')

__advertised_service = {
    "Cache-Control": _CACHE_CONTROL,
    "Server": _SERVER,
    "EXT": "",
    "USN": f"uuid:{_UUID}::upnp:rootdevice",
    "ST": "upnp:rootdevice"
}
__date_format = "%a, %d %b %Y %H:%M:%S %Z"


def generate_ssdp_httpok_packets(location, host: str, port: int):
    __advertised_service['Date'] = datetime.now().astimezone(get_localzone()).strftime(__date_format)
    __advertised_service['Location'] = location
    __advertised_service['Host'] = f'{host}:{port}'

    body = 'HTTP/1.1 200 OK\r\n' + \
           '\r\n'.join([f'{k}:{v}' for k, v in __advertised_service.items()]) + '\r\n' + \
           '\r\n'.join(_ADDITIONAL_HEADERS_LIST) + '\r\n' + \
           '\r\n'
    return body.encode()
