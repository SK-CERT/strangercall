#!/usr/bin/env python3
#
# single purpose TCP server accepting connections and receiving UPnP requests
# NOTE: connections can be closed only from the client, thus this 'server' keeps all connections active

import configparser
import logging
import socket
import threading
from datetime import datetime
from sys import stdout
from tzlocal import get_localzone

from honeypot.services import generate_description_xml_response

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
config = config_parser['upnp']

### CONFIG VARS ###
# min log level
_LOG_LEVEL = config_parser['global'].get('log_level', fallback='info').upper()
_UPNP_LISTEN_ADDR = config.get('listen_addr', fallback='0.0.0.0')
_UPNP_LISTEN_PORT = config.getint('listen_port', fallback=1784)
_UPNP_LISTEN_BUFFER = config.getint('listen_buffer', fallback=32768)
_UPNP_SEND_BUFFER = config.getint('send_buffer', fallback=1)
# max connection allowed per socket
# FIXME: consider removing, should be constant ... chnage it to the max active connections???
_UPNP_MAX_CONNECTIONS = config.getint('max_connections', fallback=1)
_ACTIVE_CONNECTION_TIMEOUT = config.getint('active_conn_timeout', fallback=5)

# description xml listen endpoint
_SERVICES_DESCRIPTION_PATH = config.get('description_path')
_ENDPOINT_URL = config.get('listen_description_endpoint', fallback='/description.xml')

# RESPONSE related variables
_UPNP_RESPONSE_TIMEOUT_HEADER = config.get('timeout_header', fallback='Second-180')
_UPNP_RESPONSE_SERVER_HEADER = config.get('server_header',
                                          fallback='Linux/i686 UPnP/1.0 DLNADOC/1.50 LGE_DLNA_SDK/04.28.17')
# UPNP SUBSCRIBE response behavior [no = no response, ok = 200 ok, slow_ok = slow 200 ok]
_SUBSCRIBE_RESPONSE_BEHAVIOR = config.get('response', fallback='no')
__ALLOWED_RESPONSE_BEHAVIORS = ['no', 'ok', 'slow_ok']

__date_format = "%a, %d %b %Y %H:%M:%S %Z"
_RESPONSE_HEADERS = "HTTP/1.1 200 OK\r\n" + \
                    "Date: {date}\r\n" + \
                    "SERVER: {server}\r\n" + \
                    "CONTENT-LENGTH: {length}\r\n" + \
                    "TIMEOUT: {timeout}\r\n" + \
                    "\r\n"

_DESCRIPTION_REQUEST_LINE = f"GET {_ENDPOINT_URL} HTTP/1.1"
_SUBSCRIBE_REQUEST_LINE = "SUBSCRIBE"

# intialize logger
log = logging.getLogger('hon_upnp')
log.setLevel(_LOG_LEVEL)
formatter = logging.Formatter('%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(stream=stdout)
handler.setFormatter(formatter)
log.addHandler(handler)

# check SUBSCRIBE request behaviors
if _SUBSCRIBE_RESPONSE_BEHAVIOR not in __ALLOWED_RESPONSE_BEHAVIORS:
    log.error(
        f'unknown response behavior "{_SUBSCRIBE_RESPONSE_BEHAVIOR}" - use on of ({",".join(__ALLOWED_RESPONSE_BEHAVIORS)})')
    exit(1)


def response(socket: socket.socket, host):
    if _SUBSCRIBE_RESPONSE_BEHAVIOR == 'no':
        return
    elif _SUBSCRIBE_RESPONSE_BEHAVIOR in ['ok', 'slow_ok']:
        # TODO: move response generation to services.py
        date_header = datetime.now().astimezone(get_localzone()).strftime(__date_format)
        data = _RESPONSE_HEADERS.format(date=date_header,
                                        server=_UPNP_RESPONSE_SERVER_HEADER,
                                        length=0,
                                        timeout=_UPNP_RESPONSE_TIMEOUT_HEADER).encode()
        socket.sendto(data, host)
        log.debug(f'[data to] {host} {data}')


def response_description_xml(socket: socket.socket, host):
    try:
        data = generate_description_xml_response(_SERVICES_DESCRIPTION_PATH)
        socket.send(data)
        log.debug(f'[data to] {host} xml description bytes data')
    except FileNotFoundError as e:
        log.error(e)


# receive messages until socket is open
# notify when disconnected
def resolve_tcp_connection(socket_fp, host):
    __msg = b'start'

    # TODO: check if the condition is satisfactory
    while __msg != b'':
        __msg = socket_fp.recv(_UPNP_LISTEN_BUFFER)
        log.debug(f'[data from] {host} {__msg}')
        if __msg.decode('utf-8').startswith(_DESCRIPTION_REQUEST_LINE):
            response_description_xml(socket_fp, host)
        elif __msg.decode('utf-8').startswith(_SUBSCRIBE_REQUEST_LINE):
            response(socket_fp, host)

    log.info(f'[-] {host} DISCONNECTED')


def counter():
    from time import sleep
    active_connections = 0

    while True:
        __no_threads = len(threading.enumerate()) - 2
        if __no_threads != active_connections:
            log.info(f'current active connections: {__no_threads}')
            active_connections = __no_threads
        sleep(_ACTIVE_CONNECTION_TIMEOUT)


def main():
    # initialize socket listening on UDP/1900
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((_UPNP_LISTEN_ADDR, _UPNP_LISTEN_PORT))
    sock.listen(_UPNP_MAX_CONNECTIONS)
    if not sock:
        log.error('failed to establish socket')
        exit(1)

    # daemon thread keeping track of active connections
    active_connection_counter_thread = threading.Thread(target=counter, name='active_connection_counter', daemon=True)
    active_connection_counter_thread.start()

    log.info(f'Started UPnP listener on {_UPNP_LISTEN_ADDR}:{_UPNP_LISTEN_PORT}')
    # accept new connection forever
    while True:
        socket_fp, host = sock.accept()
        log.info(f'[+] {host} CONNECTED')

        thread = threading.Thread(target=resolve_tcp_connection, args=(socket_fp, host), name=f'{host[0]}:{host[1]}',
                                  daemon=True)
        thread.start()


if __name__ == '__main__':
    main()
