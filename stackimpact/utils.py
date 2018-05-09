
import time
import uuid
import base64
import hashlib



def millis():
    return int(round(time.time() * 1000))


def timestamp():
    return int(time.time())


def base64_encode(s):
    return base64.b64encode(s.encode('utf-8')).decode('utf-8')


def base64_decode(b):
    return base64.b64decode(b).decode('utf-8')


def generate_uuid():
    return str(uuid.uuid4())


def generate_sha1(text):
    sha1_hash = hashlib.sha1()
    sha1_hash.update(text.encode('utf-8'))
    return sha1_hash.hexdigest()

