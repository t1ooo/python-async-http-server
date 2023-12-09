import signal
import asyncio
from asyncio import exceptions as asyncio_exc
from .context import Ctx
from .http_status import HTTPStatus
import inspect
from typing import Any, Awaitable, Callable, Generic, TypeVar
from .headers import parse_headers
from .constants import BUF_SIZE, READ_TIMEOUT_S, SERVER_NAME
from .date import http_date_now
from .exceptions import HttpException
from .handler import AsyncHandler
from .middleware import Middleware
from .request import Request
from .response import Response, error_response
from .router import Router
from .logger import logger


class Server(Generic[Ctx]):
    def __init__(
        self,
        router: Router[Ctx],
        middlewares: list[Middleware[Ctx]] | None = None,
        before_server_start: Callable[[Ctx], Awaitable[None]] | None = None,
        after_server_stop: Callable[[Ctx], Awaitable[None]] | None = None,
        ctx: Ctx = None,
    ) -> None:
        self._router = router
        self._middlewares = middlewares or []
        self._before_server_start = before_server_start
        self._after_server_stop = after_server_stop
        self._ctx = ctx

    def _wrap(self, handler: AsyncHandler[Ctx]) -> AsyncHandler[Ctx]:
        """wrap handler with middlewares like `middleware(middleware2(handler))`"""
        for m in reversed(self._middlewares):
            handler = m(handler)
        return handler

    async def _client_connected_cb(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            # TODO: add writer timeout?
            reader = _timeouted(reader, READ_TIMEOUT_S)

            logger.debug("---------------- START REQUEST ----------------")

            address = writer.get_extra_info("peername")
            method, path, protocol = await _parse_start_line(await reader.readline())

            logger.debug(f"start line: {address} {method} {path} {protocol}")

            route = self._router.match(path, method)
            if route is None:
                logger.debug(f"not found: {path} {method}")
                raise HttpException(HTTPStatus.NOT_FOUND)

            logger.debug(f"matched route: {vars(route)}")

            headers = parse_headers(await reader.readuntil(b"\r\n\r\n"))
            logger.debug(f"headers: {vars(headers)}")

            req = Request(
                reader,
                address,
                method,
                path,
                protocol,
                headers,
                route.path_params,
                self._ctx,
            )
            logger.debug(f"request: {vars(req)}")

            handler = self._wrap(route.handler)
            resp = await handler(req)

            await self._write_response(resp, writer)

        except HttpException as e:
            logger.exception(e)
            resp = error_response(e.status)
            await self._write_response(resp, writer)
        except Exception as e:
            logger.exception(e)
            resp = error_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            await self._write_response(resp, writer)
        finally:
            writer.close()

    async def _write_response(self, resp: Response, writer: asyncio.StreamWriter):
        try:
            # write headers
            headers = {
                "Server": SERVER_NAME,
                "Date": http_date_now(),
            }

            for k, v in headers.items():
                resp.headers[k] = v

            if isinstance(resp.body, (str, bytes)):
                resp.headers["Content-Length"] = str(len(resp.body))

            # TODO: set "Content-Type" if not set

            logger.debug(f"response: {vars(resp)}")

            # write first line
            writer.write(f"HTTP/1.1 {resp.status.value}\r\n".encode())

            # write headers
            for key, val in resp.headers.items():
                writer.write(f"{key}: {val}\r\n".encode())

            # write cookies
            if len(resp.cookies) > 0:
                writer.write((resp.cookies.output() + "\r\n").encode())

            # write new line before body
            writer.write(f"\r\n".encode())

            # write body
            if isinstance(resp.body, bytes):
                writer.write(resp.body)
            elif isinstance(resp.body, str):
                writer.write(resp.body.encode())
            else:
                while True:
                    chunk = await resp.body.read(BUF_SIZE)
                    if not chunk:
                        break
                    writer.write(chunk)

            await writer.drain()
        finally:
            await resp.close()

    async def run(self, host: str, port: int):
        logger.info(f"serve http://{host}:{port}")

        if self._before_server_start:
            await self._before_server_start(self._ctx)

        server = await asyncio.start_server(self._client_connected_cb, host, port)

        # handle SIGINT(ctrl_c)
        async def stop_server():
            logger.info("stop server")

            server.close()
            await server.wait_closed()

            if self._after_server_stop:
                await self._after_server_stop(self._ctx)

        loop = asyncio.get_event_loop()

        for signame in ["SIGINT"]:
            loop.add_signal_handler(
                getattr(signal, signame), lambda: asyncio.create_task(stop_server())
            )

        # run server
        async with server:
            try:
                await server.serve_forever()
            except asyncio_exc.CancelledError:
                pass


async def _parse_start_line(data: bytes) -> tuple[str, str, str]:
    method, path, protocol = data.decode("iso-8859-1").rstrip("\r\n").split(" ")
    return method, path, protocol


_Obj = TypeVar("_Obj")


def _add_timeout(
    f: Callable[..., Awaitable[_Obj]], timeout: float
) -> Callable[..., Awaitable[_Obj]]:
    async def fn(*args: Any, **kwargs: Any) -> _Obj:
        return await asyncio.wait_for(f(*args, **kwargs), timeout=timeout)

    return fn


def _timeouted(obj: _Obj, timeout: float) -> _Obj:
    """Add the timeout to all of the object's asynchronous public methods."""
    for key, val in inspect.getmembers(obj):
        if inspect.iscoroutinefunction(val) and key[0] != "_":
            setattr(obj, key, _add_timeout(val, timeout))
    return obj
