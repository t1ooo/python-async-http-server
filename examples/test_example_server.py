import re
import subprocess
from tempfile import NamedTemporaryFile
from time import sleep
import pytest
import requests
import datetime

BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    p = subprocess.Popen("make example".split(" "))
    sleep(5)  # wait for the server to start
    yield
    p.terminate()


def common_checks(resp: requests.Response, status_code: int = 200):
    assert resp.status_code == status_code

    assert resp.headers["Server"] == "Python Async HTTP Server"

    dt = datetime.datetime.strptime(resp.headers["Date"], "%a, %d %b %Y %H:%M:%S %Z")
    assert isinstance(dt, datetime.datetime)

    assert resp.headers["Content-Length"] == str(len(resp.content))


def test_all():
    # test html response
    resp = requests.get(BASE_URL + "/html_handler")
    common_checks(resp)
    assert resp.headers["Content-Type"] == "text/html; charset=utf-8"
    assert resp.content == b"html_handler"

    # should work with a slash at the end of path
    resp = requests.get(BASE_URL + "/html_handler/")
    common_checks(resp)
    assert resp.headers["Content-Type"] == "text/html; charset=utf-8"
    assert resp.content == b"html_handler"

    # test an unsupported http method
    # should return 404 for an unsupported http method
    resp = requests.post(BASE_URL + "/html_handler")
    common_checks(resp, 404)

    # test and unsupported path
    # should return 404 for an unsupported path
    resp = requests.post(BASE_URL + "/random_path_4")
    common_checks(resp, 404)

    # test text response
    resp = requests.get(BASE_URL + "/text_handler")
    common_checks(resp)
    assert resp.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert resp.content == b"text_handler"

    # test json request/response
    # should get the same json
    json = {"test1": "test_value1", "test2": "test_value2"}
    resp = requests.post(BASE_URL + "/json_handler", json=json)
    common_checks(resp)
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json() == json

    # test json request/response
    # should get nothing if the json has not been sent
    resp = requests.post(BASE_URL + "/json_handler", json={})
    common_checks(resp)
    assert resp.headers["Content-Type"] == "application/json"
    assert resp.json() == {}

    # test redirect
    resp = requests.get(BASE_URL + "/redirect_handler", allow_redirects=False)
    common_checks(resp, 301)
    assert resp.headers["Location"] == "https://google.com"
    assert resp.content == b""

    # test file response
    resp = requests.get(BASE_URL + "/file_handler")
    common_checks(resp)
    assert (
        resp.headers["Content-Disposition"]
        == 'attachment; filename="test%20test%20test"'
    )
    assert resp.content == b"file_handler"

    # test query params
    resp = requests.get(BASE_URL + "/query_params_handler?a=1&a=2&b=3")
    common_checks(resp)
    assert resp.content == b"{'a': ['1', '2'], 'b': ['3']}"

    # test query params
    # should get nothing if the query params are empty
    resp = requests.get(BASE_URL + "/query_params_handler")
    common_checks(resp)
    assert resp.content == b"{}"

    # test path params
    resp = requests.get(BASE_URL + "/person/123/item/456")
    common_checks(resp)
    assert resp.content == b"{'person': '123', 'item': '456'}"

    # test cookies
    # should get the same cookies
    cookies = {"test1": "test_value1", "test2": "test_value2"}
    resp = requests.get(BASE_URL + "/cookies_handler", cookies=cookies)
    common_checks(resp)
    assert resp.cookies == cookies

    # test cookies
    # should get empty cookies if the cookies has not been sent
    resp = requests.get(BASE_URL + "/cookies_handler")
    common_checks(resp)
    assert len(resp.cookies) == 0

    # test form urlencoded
    resp = requests.post(BASE_URL + "/form_urlencoded_handler", data={"test": "test"})
    common_checks(resp)
    assert resp.content == b"{'test': ['test']}"

    # test form urlencoded
    # should return nothing if the form  has not been sent
    resp = requests.post(BASE_URL + "/form_urlencoded_handler", data={})
    common_checks(resp)
    assert resp.content == b"{}"

    # test upload file
    with NamedTemporaryFile() as tfp:
        tfp.write(b"test")
        tfp.seek(0)
        files = {"upload_file": ("test_file", tfp)}
        data = {"test": "test"}

        common_checks(resp)
        resp = requests.post(
            BASE_URL + "/multipart_form_handler", files=files, data=data
        )
        assert (
            resp.content
            == b"form:{'test': ['test']}, files:[FieldStorage('upload_file', 'test_file', b'test')]"
        )

    # test static content
    for i in range(3):
        resp = requests.get(BASE_URL + f"/static/{i}.txt")
        common_checks(resp)
        assert resp.content == f"file_{i}".encode()
        assert "Content-Disposition" in resp.headers
        assert "Last-Modified" in resp.headers

    # should return 404 if the file does not exist
    for i in range(3, 6):
        resp = requests.get(BASE_URL + f"/static/{i}.txt")
        common_checks(resp, 404)

    # test basic_auth_middleware
    basic = ("user", "pass")
    resp = requests.get(BASE_URL + "/sensitive_data_handler", auth=basic)
    common_checks(resp)
    assert resp.content == b"sensitive_data_handler"

    # test basic_auth_middleware
    # should return 404 if the auth data has not bee sent
    resp = requests.get(BASE_URL + "/sensitive_data_handler")
    common_checks(resp, 401)

    # test ctx
    resp = requests.get(BASE_URL + "/ctx_handler")
    common_checks(resp)

    # test custom_response
    resp = requests.get(BASE_URL + "/custom_response_handler")
    common_checks(resp)

    # test request headers
    resp = requests.get(BASE_URL + "/headers_handler")
    common_checks(resp)

    resp = requests.post(BASE_URL + "/body_handler", data="123")
    common_checks(resp)
    assert resp.content == b"123"

    resp = requests.get(BASE_URL + "/address_handler")
    common_checks(resp)
    assert re.match(r"^\('127\.0\.0\.1', \d+\)$", resp.text)

    resp = requests.get(BASE_URL + "/method_handler")
    common_checks(resp)
    assert resp.content == b"GET"

    resp = requests.get(BASE_URL + "/path_handler")
    common_checks(resp)
    assert resp.content == b"/path_handler"
