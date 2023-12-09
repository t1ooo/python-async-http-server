from http.client import HTTPMessage
from http.client import parse_headers as http_parse_headers
from io import BytesIO

Headers = HTTPMessage


def headers_from_dict(d: dict[str, str]) -> Headers:
    h = Headers()
    for k, v in d.items():
        h[k] = v
    return h


def parse_headers(data: bytes) -> Headers:
    buf = BytesIO(data)
    return http_parse_headers(buf)
