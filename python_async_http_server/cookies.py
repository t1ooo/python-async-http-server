from http.cookies import SimpleCookie

Cookies = SimpleCookie


def parse_cookies(s: str) -> Cookies:
    cookies = SimpleCookie()
    cookies.load(s)
    return cookies
