import json
import gzip
import sys
import os
import socket

from io import BytesIO

from .utils import timestamp, base64_encode
from .runtime import runtime_info


if runtime_info.PYTHON_2:
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib import urlencode
else:
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.parse import urlencode


class APIRequest(object):
    def __init__(self, agent):
        self.agent = agent   

    def post(self, endpoint, payload):
        agent_key_64 = base64_encode(self.agent.get_option('agent_key') + ':').replace('\n', '')
        headers = {
            'Accept-Encoding': 'gzip',
            'Authorization': "Basic %s" % agent_key_64,
            'Content-Type': 'application/json',
            'Content-Encoding': 'gzip'
        }

        host_name = 'undefined'
        try:
            host_name = socket.gethostname()
        except Exception:
            self.agent.exception()

        req_body = {
            'runtime_type':    'python',
            'runtime_version': '{0.major}.{0.minor}.{0.micro}'.format(sys.version_info),
            'runtime_path':    sys.prefix,
            'agent_version':   self.agent.AGENT_VERSION,
            'app_name':        self.agent.get_option('app_name'),
            'app_version':     self.agent.get_option('app_version'),
            'app_environment': self.agent.get_option('app_environment'),
            'host_name':       self.agent.get_option('host_name', host_name),
            'process_id':      os.getpid(),
            'run_id':          self.agent.run_id,
            'run_ts':          self.agent.run_ts,
            'sent_at':         timestamp(),
            'payload':         payload,
        }

        gzip_out = BytesIO()
        with gzip.GzipFile(fileobj=gzip_out, mode="w") as out_file:
          out_file.write(json.dumps(req_body).encode('utf-8'))
          out_file.close()

        gzip_out_val = gzip_out.getvalue()
        if isinstance(gzip_out_val, str):
            req_body_gzip = bytearray(gzip_out.getvalue())
        else:
            req_body_gzip = gzip_out.getvalue()

        request = Request(
            url = self.agent.get_option('dashboard_address') + '/agent/v1/' + endpoint,
            data = req_body_gzip,
            headers = headers)

        response = urlopen(request, timeout = 20)

        result_data = response.read()

        if response.info():
            content_type = response.info().get('Content-Encoding')
            if content_type == 'gzip':
                result_data = gzip.GzipFile('', 'r', 0, BytesIO(result_data)).read()

        response.close()

        return json.loads(result_data.decode('utf-8'))


def python_version():
    [sys.version_info.major,'',sys.version_info.minor + sys.version_info.micro]
