from .http_status import HTTPStatus


class HttpException(Exception):
    def __init__(self, status: HTTPStatus):
        self.status = status
