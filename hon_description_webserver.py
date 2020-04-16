#!/usr/bin/env python3
#
# HTTP server serving the service description XML file
#
# usage:
#    python3 hon_description_webserver.py

import configparser
import logging
from sys import stdout
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

config_parser = configparser.ConfigParser()
config_parser.read('config.ini')
config = config_parser['web_server']

### CONFIG VARS ###
_LOG_LEVEL = config_parser['global'].get('log_level', 'info').upper()
_SERVICES_DESCRIPTION_PATH = config.get('description_path')
_ENDPOINT_HOST = config.get('listen_addr', fallback='0.0.0.0')
_ENDPOINT_PORT = config.getint('listen_port', fallback=5000)
_ENDPOINT_URL = config.get('listen_endpoint', fallback='/description.xml')

_SERVER_HEADER = config.get('server_header', fallback=None)
_ADDITIONAL_HEADERS_LIST = config.get('header_tail', fallback='').split('\r\n')

_RESPONSE_HEADERS = {
    'Content-Language': 'en',
    'Content-Type': 'text/xml; charset="utf-8"'
}
if _SERVER_HEADER:
    _RESPONSE_HEADERS['Server'] = _SERVER_HEADER
# add additional headers to the response headers
for header in _ADDITIONAL_HEADERS_LIST:
    name = header.split(': ')[0]
    value = ': '.join(header.split(': ')[1:])
    _RESPONSE_HEADERS[name] = value


# initialize logger
log = logging.getLogger("werkzeug")
log.setLevel(_LOG_LEVEL)
formatter = logging.Formatter('%(asctime)-15s %(name)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(stream=stdout)
handler.setFormatter(formatter)
log.addHandler(handler)


class ServicesDescriptionEndpoint:
    def __init__(self):
        self.__url_map = Map([
            Rule(_ENDPOINT_URL, endpoint='services_desc', methods=["GET"])
        ])

    def __dispatch_request(self, request):
        # process request arguemnts and shit
        request_adapter = self.__url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = request_adapter.match()
            return getattr(ServicesDescriptionEndpoint, 'on_' + endpoint)(request, **values)
        except HTTPException as e:
            return e

    @staticmethod
    def on_services_desc(request):
        try:
            with open(_SERVICES_DESCRIPTION_PATH, 'rb') as fp:
                data = fp.read()

            return Response(data, mimetype='text/xml', headers=_RESPONSE_HEADERS)
        except HTTPException as e:
            raise NotFound()

    def application(self, environ, start_response):
        request = Request(environ)
        response = self.__dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.application(environ, start_response)


def main():
    adapter = ServicesDescriptionEndpoint()
    run_simple(_ENDPOINT_HOST, _ENDPOINT_PORT, adapter)


if __name__ == '__main__':
    main()