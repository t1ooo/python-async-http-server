from urllib.parse import parse_qs, urlparse

Query = dict[str, list[str]]


def parse_query(url: str) -> Query:
    return parse_qs(urlparse(url).query)
