import api
import hashlib
import datetime
import pytest
import threading
import time
from http.server import HTTPServer

@pytest.fixture
def valid_token():
    login = "user"
    account = "acc"
    h = account + login + api.SALT
    return hashlib.sha512(h.encode("utf-8")).hexdigest()

@pytest.fixture
def admin_token():
    h = datetime.datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT
    return hashlib.sha512(h.encode("utf-8")).hexdigest()

@pytest.fixture
def base_request(valid_token):
    return {
        "account": "acc",
        "login": "user",
        "token": valid_token,
        "method": "online_score",
        "arguments": {}
    }

@pytest.fixture
def base_request_admin(admin_token):
    return {
        "account": "acc",
        "login": api.ADMIN_LOGIN,
        "token": admin_token,
        "method": "online_score",
        "arguments": {}
    }


@pytest.fixture(scope="session")
def server():
    server = HTTPServer(("localhost", 8081), api.MainHTTPHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(1)
    yield server
    server.shutdown()