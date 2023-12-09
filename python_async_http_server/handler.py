import os
from typing import Any, Awaitable, Callable
from .context import Ctx
from .request import Request
from .response import Response, file_response

AsyncHandler = Callable[[Request[Ctx]], Awaitable[Response]]


async def handle_static_files(
    folder: str, path_begin: str, req: Request[Any]
) -> Response:
    path = req.path
    path = folder + path[len(path_begin) :]
    path = os.path.abspath(path)
    return await file_response(path)
