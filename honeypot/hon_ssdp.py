#!/usr/bin/env python3
#
# SSDP socket listener on UDP/1900. After receiving a M-SEARCH request, it responses with 'HTTP 200 OK' message
# responses to any ST header with the same response

import asyncio
import configparser
import logging
import socket
from async_upnp_client.ssdp import SsdpProtocol
from datetime import datetime
from sys import stdout
from threading import Thread, Lock
from typing import Any, Mapping, MutableMapping, Tuple, Callable, Awaitable

from honeypot.services import generate_ssdp_httpok_packets

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
_SSDP_RATELIMIT_ENABLED = config.getboolean('enable_ratelimit', fallback=True)
_SSDP_SECOND_RATELIMIT = config.getint('ratelimit_second', fallback=1)
_SSDP_MINUTE_RATELIMIT = config.getint('ratelimit_minute', fallback=5)
_SSDP_HOUR_RATELIMIT = config.getint('ratelimit_hour', fallback=10)
_RATELIMIT_METRICS = {
    'last_hour': _SSDP_HOUR_RATELIMIT,
    'last_minute': _SSDP_MINUTE_RATELIMIT,
    'last_second': _SSDP_SECOND_RATELIMIT
}

log = logging.getLogger('hon_ssdp')

__last_cleanup_time_mutex = Lock()
__ratelimit_stats_mutex = Lock()
__ratelimit_stats = {}
__last_cleanup_time = {x: datetime.now() for x in _RATELIMIT_METRICS.keys()}


def _increment_ratelimit_counters(ip):
    with __ratelimit_stats_mutex:
        if ip not in __ratelimit_stats:
            __ratelimit_stats[ip] = {m: 1 for m in _RATELIMIT_METRICS.keys()}
        else:
            for m in _RATELIMIT_METRICS.keys():
                __ratelimit_stats[ip][m] += 1


def _ratelimit_cleanup():
    from time import sleep

    def _ratelimit_cleanup_for_key(key: str):
        with __ratelimit_stats_mutex:
            to_delete = set()
            for ip in __ratelimit_stats.keys():
                __ratelimit_stats[ip][key] = 0

                ip_stats = __ratelimit_stats[ip]
                if ip_stats['last_second'] == ip_stats['last_minute'] == ip_stats['last_hour'] == 0:
                    to_delete.add(ip)

            # delete the ip with all zero stats toremove historic data
            for ip in to_delete:
                del __ratelimit_stats[ip]

        __last_cleanup_time[key] = datetime.now()

    while True:
        sleep(1)
        with __last_cleanup_time_mutex:
            _ratelimit_cleanup_for_key('last_second')
            __last_cleanup_time['last_second'] = datetime.now()
            if (datetime.now() - __last_cleanup_time['last_minute']).total_seconds() >= 60:
                _ratelimit_cleanup_for_key('last_minute')
            if (datetime.now() - __last_cleanup_time['last_hour']).total_seconds() >= 3600:
                _ratelimit_cleanup_for_key('last_hour')


def ok_to_send(ip: str) -> bool:
    with __ratelimit_stats_mutex:
        for m, lim in _RATELIMIT_METRICS.items():
            if __ratelimit_stats[ip][m] > lim:
                return False

    return True


# only for debugging
def generate_ratelimiting_current_state_lines():
    for ip, stats in __ratelimit_stats.items():
        yield f'RATELIMIT | {ip};  sec: {stats["last_second"]};  min: {stats["last_minute"]};  hour: {stats["last_hour"]}'


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
        if _SSDP_RATELIMIT_ENABLED:
            _increment_ratelimit_counters(headers['_address'].split(':')[0])
        raw_headers = '\r\n'.join([f'{k}:{v}' for k, v in headers.items() if not k.startswith('_')])
        data = (request_line + raw_headers).encode()
        log.info(f'FROM {headers["_address"]} {len(data)} bytes - {data}')
        if "M-SEARCH" in request_line and 'ST' in headers:
            if _SSDP_RATELIMIT_ENABLED and not ok_to_send(headers['_address'].split(':')[0]):
                return
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


async def main_loop():
    # callable for received M-SEARCH
    async def on_msearch(data: Mapping[str, Any]):
        log.debug(f'received valid M-SEARCH responsing with HTTP 200 OK; {data}')
        await async_httpok(location=_SSDP_HEADER_LOCATION,
                           source_ip=_SSDP_SOURCE_ADDR,
                           target=(data['_address'].split(':')[0], int(data['_address'].split(':')[1])))

    listener = DummySSDPListener(on_msearch=on_msearch, source_bind=_SSDP_LISTEN_BIND)

    await listener.async_start()
    try:
        while True:
            for msg in generate_ratelimiting_current_state_lines():
                log.debug(msg)

            log.debug(f'currently rate limiting {len(__ratelimit_stats.keys())} ips')
            log.info(f'ALIVE idling for {_WATCHDOG_TIMEOUT / 60} minutes...')
            await asyncio.sleep(_WATCHDOG_TIMEOUT)
    except KeyboardInterrupt:
        log.debug('KeyboardInterrupt')
        await listener.async_stop()
        raise


def main():
    # intialize logger
    log.setLevel(_LOG_LEVEL)
    formatter = logging.Formatter('%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
    handler = logging.StreamHandler(stream=stdout)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    if _SSDP_RATELIMIT_ENABLED:
        ratelimit_cleanup_thread = Thread(target=_ratelimit_cleanup, daemon=True)
        ratelimit_cleanup_thread.start()
        log.debug(f'started rate limiting cleanup thread')

    loop = asyncio.get_event_loop()
    log.info(f'Started SSDP listener on {_SSDP_LISTEN_BIND_STR}')
    loop.run_until_complete(main_loop())


if __name__ == '__main__':
    main()
