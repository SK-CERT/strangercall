#!/usr/bin/env python3
#
# SSDP socket listener on UDP/1900. After receiving a M-SEARCH request, it responses with 'HTTP 200 OK' message
# responses only for ST: upnp:rootdevice
#
# usage:
#    python3 hon_ssdp.py

import asyncio
import configparser
import logging
import socket
from async_upnp_client.ssdp import SsdpProtocol
from sys import stdout
from typing import Any, Mapping, MutableMapping, Tuple, Callable, Awaitable

from services import generate_ssdp_httpok_packets

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
config = config_parser['ssdp']

### CONFIG VARS ###
_LOG_LEVEL = config_parser['global'].get('log_level', fallback='info').upper()
_WATCHDOG_TIMEOUT = config.getint('watchdog_timeout', fallback=60) * 60  # converted to seconds
_SSDP_LISTEN_ADDR = config.get('listen_addr', fallback='0.0.0.0')
_SSDP_LISTEN_PORT = 1900
_SSDP_LISTEN_BIND = (_SSDP_LISTEN_ADDR, _SSDP_LISTEN_PORT)
_SSDP_LISTEN_BIND_STR = f'{_SSDP_LISTEN_ADDR}:{_SSDP_LISTEN_PORT}'
_SSDP_SOURCE_ADDR = config.get('source_addr')
# SSDP 'HTTP OK' response headers
_SSDP_HEADER_LOCATION = config['location_header']
_SSDP_HEADER_ST = config.get('accept_st_header', fallback='upnp:rootdevice')


class DummySSDPListener:

    def __init__(self, on_msearch: Callable[[Mapping[str, str]], Awaitable], source_bind):
        self.__on_msearch = on_msearch
        self.__source_bind = source_bind
        self.__event_loop = asyncio.get_event_loop()
        self.__transport = None

        self.__connect = self.__setup_socket(self.__source_bind)

    def __setup_socket(self, listen_host_bind: Tuple[str, int]):
        # create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(listen_host_bind)

        connect = self.__event_loop.create_datagram_endpoint(
            lambda: SsdpProtocol(self.__event_loop, on_data=self.__on_request),
            sock=sock,
        )

        return connect

    async def __on_request(self, request_line: str, headers: MutableMapping[str, str]):
        # TODO: discuss the request condition
        raw_headers = '\r\n'.join([f'{k}:{v}' for k,v in headers.items() if not k.startswith('_')])
        data = (request_line + raw_headers).encode()
        log.info(f'FROM {headers["_address"]} {len(data)} bytes - {data}')
        if ("M-SEARCH" in request_line and 'ST' in headers) and headers['ST'] == _SSDP_HEADER_ST:
            await self.__on_msearch(headers)

    # Start listening for notifications
    async def async_start(self):
        self.__transport, _ = await self.__connect

    # Stop listening for notifications
    async def async_stop(self):
        if self.__transport:
            self.__transport.close()


# send http ok message
async def async_httpok(location, source_ip: str, target: Tuple[str, int]):
    async def send_httpok(transport):
        packet = generate_ssdp_httpok_packets(location=location, host=source_ip, port=source_port)
        log.info(f'TO {target[0]}:{target[1]} {len(packet)} bytes - {packet}')
        transport.sendto(packet, target)

    event_loop = asyncio.get_event_loop()

    # create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((source_ip, _SSDP_LISTEN_PORT))

    source_port = sock.getsockname()[1]
    log.debug(f'setup up socket on {source_ip}:{source_port}')

    connect_advertiser = event_loop.create_datagram_endpoint(
        lambda: SsdpProtocol(event_loop, on_connect=send_httpok, on_data=None),
        sock=sock
    )

    _transport, _ = await connect_advertiser
    _transport.close()


async def main():
    # callable for received M-SEARCH
    async def on_msearch(data: Mapping[str, Any]):
        log.debug(f'received valid M-SEARCH responsing with HTTP 200 OK')
        await async_httpok(location=_SSDP_HEADER_LOCATION,
                           source_ip=_SSDP_SOURCE_ADDR,
                           target=(data['_address'].split(':')[0], int(data['_address'].split(':')[1])))

    listener = DummySSDPListener(on_msearch=on_msearch, source_bind=_SSDP_LISTEN_BIND)

    await listener.async_start()
    try:
        while True:
            log.info(f'ALIVE idling for {_WATCHDOG_TIMEOUT / 60} minutes...')
            await asyncio.sleep(_WATCHDOG_TIMEOUT)
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt')
        await listener.async_stop()
        raise


if __name__ == '__main__':
    # intialize logger
    log = logging.getLogger('hon_ssdp')
    log.setLevel(_LOG_LEVEL)
    formatter = logging.Formatter('%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
    handler = logging.StreamHandler(stream=stdout)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    loop = asyncio.get_event_loop()
    log.info(f'Started SSDP listener on {_SSDP_LISTEN_BIND_STR}')
    loop.run_until_complete(main())
