import base64
from .context import Ctx
from .http_status import HTTPStatus
from typing import Any, Callable
from .exceptions import HttpException
from .request import Request
from .response import Response
from .handler import AsyncHandler

Middleware = Callable[[AsyncHandler[Ctx]], AsyncHandler[Ctx]]


def add_middleware(
    m: Middleware[Ctx], *args: Any, **kwargs: Any
) -> Callable[[AsyncHandler[Ctx]], AsyncHandler[Ctx]]:
    def wrapper(h: AsyncHandler[Ctx]) -> AsyncHandler[Ctx]:
        return m(h, *args, **kwargs)

    return wrapper


def basic_auth_middleware(
    call_next: AsyncHandler[Ctx], user: str, password: str
) -> AsyncHandler[Ctx]:
    async def f(req: Request[Ctx]) -> Response:
        auth_type, data = req.headers.get("Authorization", " ").split(" ")
        if not (
            auth_type == "Basic"
            and base64.b64decode(data).decode("utf-8") == f"{user}:{password}"
        ):
            raise HttpException(HTTPStatus.UNAUTHORIZED)
        resp = await call_next(req)
        return resp

    return f
