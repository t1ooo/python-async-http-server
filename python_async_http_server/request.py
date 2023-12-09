import asyncio
import json
from tempfile import SpooledTemporaryFile
from typing import IO, Any, Awaitable, Callable, Generic, TypeVar
from .context import Ctx
from .address import Address
from .constants import BUF_SIZE, TEMP_FILE_MAX_SIZE
from .cookies import Cookies, parse_cookies
from .form import Files, Form, parse_multipart_form, parse_form_urlencoded
from .headers import Headers
from .query import Query, parse_query
from .path_params import PathParams


class Request(Generic[Ctx]):
    def __init__(
        self,
        reader: asyncio.StreamReader,
        address: Address,
        method: str,
        path: str,
        protocol: str,
        headers: Headers,
        path_params: PathParams,
        ctx: Ctx,
    ) -> None:
        self._reader = reader

        self.address = address
        self.method = method
        self.path = path
        self.protocol = protocol
        self.headers = headers
        self.path_params = path_params
        self.ctx = ctx

        self._query = _AsyncLazyValue(self._parse_query)
        self._cookies = _AsyncLazyValue(self._parse_cookies)
        self._json = _AsyncLazyValue(self._parse_json)
        self._body = _AsyncLazyValue(self._read_body)
        self._form_files = _AsyncLazyValue(self._parse_form)

    async def close(self):
        if self._body.received:
            self._body.get().close()

    async def body(self) -> IO[Any]:
        return await self._body.get()

    async def body_data(self) -> bytes:
        body = await self.body()
        body.seek(0)

        return await asyncio.to_thread(body.read)

    async def _read_body(self) -> IO[Any]:
        # Why do we copy the body in SpooledTemporaryFile?
        #   We cannot read the body from the stream multiple times.
        #   We can read it once from the stream into memory, but it may be too big.
        #   FieldStorage, needed for multipart form parsing, accepts synchronous IO as input.
        n = int(self.headers.get("Content-Length", 0))
        tfp = SpooledTemporaryFile(max_size=TEMP_FILE_MAX_SIZE)
        await _copy_io_async_to_sync(self._reader, tfp, n)
        tfp.seek(0)
        return tfp

    async def json(self) -> Any:
        return await self._json.get()

    async def _parse_json(self) -> Any:
        return json.loads(await self.body_data())

    async def query(self) -> Query:
        return await self._query.get()

    async def _parse_query(self) -> Query:
        return parse_query(self.path)

    async def cookies(self) -> Cookies:
        return await self._cookies.get()

    async def _parse_cookies(self) -> Cookies:
        return parse_cookies(self.headers.get("Cookie", ""))

    async def form(self) -> Form:
        return (await self._form_files.get())[0]

    async def files(self) -> Files:
        return (await self._form_files.get())[1]

    async def _parse_form(self) -> tuple[Form, Files]:
        form: Form = {}
        files: Files = []

        ctype = self.headers.get("Content-Type", "")
        if ctype == "application/x-www-form-urlencoded":
            form = parse_form_urlencoded((await self.body_data()).decode())
        elif ctype.startswith("multipart/form-data"):
            body = await self.body()
            body.seek(0)
            form, files = await parse_multipart_form(self.headers, body)

        return form, files


_Value = TypeVar("_Value")


class _AsyncLazyValue(Generic[_Value]):
    def __init__(self, get_value: Callable[[], Awaitable[_Value]]):
        self._value: _Value | None = None
        self._get_value = get_value
        self.received = False

    async def get(self) -> _Value:
        if self._value is None:
            self._value = await self._get_value()
            if self._value is None:
                raise Exception("get_value must not return None")
            self.received = True
        return self._value


async def _copy_io_async_to_sync(reader: asyncio.StreamReader, writer: IO[Any], n: int):
    rem = n
    while True:
        if rem <= 0:
            break

        chunk = await reader.read(min(BUF_SIZE, rem))
        rem -= len(chunk)
        if not chunk:
            break

        await asyncio.to_thread(writer.write, chunk)
