import unittest
import sys
import threading
import time

from io import BytesIO


try:
    # python 2
    from BaseHTTPServer import HTTPServer,BaseHTTPRequestHandler
except:
    # python 3
    from http.server import HTTPServer,BaseHTTPRequestHandler

import gzip


class TestServer(threading.Thread):
    def __init__(self, port, delay = None, handler_func = None):
        self.port = port
        RequestHandler.delay = delay
        RequestHandler.handler_func = [handler_func]
        RequestHandler.response_data = '{}'
        RequestHandler.response_code = 200
        threading.Thread.__init__(self)
        self.server = HTTPServer(('localhost', self.port), RequestHandler)

    def get_request_data(self):
        return RequestHandler.request_data

    def set_response_data(self, response_data):
        RequestHandler.response_data = response_data

    def set_response_code(self, response_code):
        RequestHandler.response_code = response_code

    def run(self):
        self.server.handle_request()


class RequestHandler(BaseHTTPRequestHandler):
    delay = None
    handler_func = None
    request_data = None
    response_data = '{}'
    response_code = 200


    def do_GET(self):
        if self.delay:
            time.sleep(self.delay)

        if RequestHandler.handler_func: 
            RequestHandler.handler_func[0]()

        self.send_response(RequestHandler.response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(RequestHandler.response_data.encode('utf-8'))


    def do_POST(self):
        if self.delay:
            time.sleep(self.delay)

        self.request_url = self.path
        content_len = int(self.headers.get('content-length'))

        decompressed_data = gzip.GzipFile(fileobj=BytesIO(self.rfile.read(content_len))).read()
        RequestHandler.request_data = decompressed_data.decode('utf-8')

        self.send_response(RequestHandler.response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(RequestHandler.response_data.encode('utf-8'))
