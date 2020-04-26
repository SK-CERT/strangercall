#!/usr/bin/env python3
#
# helper file for crafting 'HTTP 200 OK' response

import configparser
from datetime import datetime
from tzlocal import get_localzone

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
# TODO: change to 'services' both here and in config example
config = config_parser['ssdp_services']

_UUID = config.get('uuid')
# FIXME: rename the config variable to 'ssdp_server_header'
_SSDP_SERVER = config.get('server_header')
# TODO: move to cofiguration file
_UPNP_SERVER = 'Linux/i686 UPnP/1.0 DLNADOC/1.50 LGE_DLNA_SDK/04.28.17'
_CACHE_CONTROL = config.get('cache-control_header', fallback='max-age=1800')
_ADDITIONAL_HEADERS_LIST = config.get('header_tail', fallback='')

# TODO: uncomment and change in config example
# _SERVICES_DESCRIPTION_PATH = config.get('description_path')

__advertised_service = {
    "Cache-Control": _CACHE_CONTROL,
    "Server": _SSDP_SERVER,
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
           _ADDITIONAL_HEADERS_LIST + '\r\n' + \
           '\r\n'
    return body.encode()


__description_response = '\r\n'.join([
    'HTTP/1.1 200 OK',
    'Content-Language: en',
    'Content-Type: text/xml; charset="utf-8"',
    'Content-Length: {length}',
    f'Server: {_UPNP_SERVER}',
    f'Date: {datetime.now().astimezone(get_localzone()).strftime(__date_format)}'
])
if _ADDITIONAL_HEADERS_LIST != '':
    __description_response = '\r\n' + _ADDITIONAL_HEADERS_LIST


def generate_description_xml_response(desc_path) -> bytes:
    # TODO: change to constant _SERVICES_DESCRIPTION_PATH
    with open(desc_path, 'rb') as fp:
        data = fp.read()
        return (__description_response + '\r\n\r\n').format(length=len(data)).encode() + data
