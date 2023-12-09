import asyncio
from .http_status import HTTPStatus
import json
import os
from typing import Any, BinaryIO
from urllib.parse import quote
from .cookies import Cookies
from .date import http_date_from_timestamp
from .logger import logger
from .exceptions import HttpException
from .headers import Headers, headers_from_dict


class AsyncReader:
    def __init__(self, fh: BinaryIO):
        self._fh = fh

    @classmethod
    async def from_path(cls, filepath: str):
        fh = await asyncio.to_thread(open, filepath, mode="rb")
        return cls(fh)

    async def close(self):
        await asyncio.to_thread(self._fh.close)

    async def read(self, n: int = -1) -> bytes:
        return await asyncio.to_thread(self._fh.read, n)

    async def __aexit__(self):
        await self.close()


class Response:
    def __init__(
        self,
        status: HTTPStatus = HTTPStatus.OK,
        headers: Headers | None = None,
        body: str | bytes | AsyncReader | None = None,
        cookies: Cookies | None = None,
    ):
        self.status = status
        self.headers = headers or Headers()
        self.body = body or b""
        self.cookies = cookies or Cookies()

    async def close(self):
        if isinstance(self.body, AsyncReader):
            await self.body.close()


def error_response(status: HTTPStatus):
    return Response(
        status,
        headers_from_dict({"Content-Type": "text/html; charset=utf-8"}),
        status.phrase,
    )


def html_response(body: str | bytes, status: HTTPStatus = HTTPStatus.OK):
    return Response(
        status, headers_from_dict({"Content-Type": "text/html; charset=utf-8"}), body
    )


def text_response(body: str | bytes, status: HTTPStatus = HTTPStatus.OK):
    return Response(
        status, headers_from_dict({"Content-Type": "text/plain; charset=utf-8"}), body
    )


def redirect_response(url: str, status: HTTPStatus = HTTPStatus.MOVED_PERMANENTLY):
    return Response(status, headers_from_dict({"Location": url}))


def json_response(obj: Any, status: HTTPStatus = HTTPStatus.OK):
    body = json.dumps(obj)
    return Response(
        status, headers_from_dict({"Content-Type": "application/json"}), body
    )


async def file_response(path: str, download_filename: str | None = None) -> Response:
    finfo = await asyncio.to_thread(_file_info, path)
    if finfo is None:
        logger.debug(f"file not found: {path}")
        raise HttpException(HTTPStatus.NOT_FOUND)
    size, last_modify = finfo

    if download_filename is None:
        download_filename = os.path.basename(path)
    content_disposition = f'attachment; filename="{quote(download_filename)}"'

    logger.debug(
        f"file_response: path={path} finfo={finfo} download_filename={download_filename}"
    )

    return Response(
        headers=headers_from_dict(
            {
                "Content-Disposition": content_disposition,
                "Content-Length": str(size),
                "Last-Modified": http_date_from_timestamp(last_modify),
                # TODO: add Content-Type
            }
        ),
        body=await AsyncReader.from_path(path),
    )


def _file_info(path: str) -> tuple[int, float] | None:
    if os.path.isfile(path) and os.access(path, os.R_OK):
        return os.path.getsize(path), os.path.getmtime(path)
    return None
