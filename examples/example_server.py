import os
import asyncio
from tempfile import NamedTemporaryFile
import logging
from python_async_http_server import *

logging.basicConfig(level=logging.INFO)


# define our app context
class SomeDb:
    async def open(self):
        print("open db")

    async def close(self):
        print("close db")


class SomeCache:
    async def open(self):
        print("open cache")

    async def close(self):
        print("close cache")


class Context:
    def __init__(self, db: SomeDb, cache: SomeCache):
        self.db = db
        self.cache = cache


# create aliases with our context for convenience
CtxRouter = Router[Context]
CtxRequest = Request[Context]
CtxAsyncHandler = AsyncHandler[Context]

router = CtxRouter()


# add the route to this handler
@router.route("/sensitive_data_handler")
# add the middleware that wrap this handler
# the order of defining decorators is important!
@add_middleware(basic_auth_middleware, "user", "pass") # type: ignore
async def sensitive_data_handler(req: CtxRequest) -> Response:
    data = "sensitive_data_handler"
    return html_response(data)


# we will wrap this handler further below without using a decorator
async def other_sensitive_data_handler(req: CtxRequest) -> Response:
    data = "other_sensitive_data_handler"
    return html_response(data)


# simple html response
@router.route("/html_handler")
async def html_handler(req: CtxRequest) -> Response:
    data = "html_handler"
    return html_response(data)


# simple text response
@router.route("/text_handler")
async def text_handler(req: CtxRequest) -> Response:
    data = "text_handler"
    return text_response(data)


# read json from request/send json in response
@router.route("/json_handler", ["POST"])
async def json_handler(req: CtxRequest) -> Response:
    data = await req.json()  # read json
    return json_response(data)  # send json


# redirect
@router.route("/redirect_handler")
async def redirect_handler(req: CtxRequest) -> Response:
    url = "https://google.com"
    return redirect_response(url)


# get cookies from request/set cookies to response
@router.route("/cookies_handler")
async def cookies_handler(req: CtxRequest) -> Response:
    cookies = await req.cookies()

    _value = cookies.get("some_key")  # get cookie by name as http.cookies.Morsel object

    resp = html_response("cookies_handler")
    for k, v in cookies.items():
        resp.cookies[k] = v.value  # set cookies to response
    return resp


# path query params like `path/a=1&a=2&b=3`
@router.route("/query_params_handler")
async def query_params_handler(req: CtxRequest) -> Response:
    query: Query = await req.query()  # something like {'a': ['1', '2'], 'b': ['3']}

    _value = query.get("some_key", [])  # get query param by name

    return html_response(f"{query}")


# path parameters
@router.route("/person/:person/item/:item")
async def path_params_handler(req: CtxRequest) -> Response:
    path_params: PathParams = (
        req.path_params
    )  # something like {'person':'john', 'item':'123'}

    _value = path_params.get("person", "")  # get path param by name

    return html_response(f"{path_params}")


# form
async def form_urlencoded_handler(req: CtxRequest) -> Response:
    form: Form = await req.form()  # something like  {'test': ['test']}

    _value = form.get("test", [])  # get form value by name

    return html_response(f"{form}")


# multipart form (form values + files)
async def multipart_form_handler(req: CtxRequest) -> Response:
    form: Form = await req.form()
    files: Files = await req.files()

    for f in files:
        print(f.name, f.filename, f.file.read()) # type: ignore

    return html_response(f"form:{form}, files:{files}")


# file response
@router.route("/file_handler")
async def file_handler(req: CtxRequest) -> Response:
    tfp = NamedTemporaryFile()
    tfp.write(b"file_handler")
    tfp.seek(0)

    path = tfp.name
    download_filename = "test test test"
    return await file_response(path, download_filename)


# get application context from CtxRequest object
@router.route("/ctx_handler")
async def ctx_handler(req: CtxRequest) -> Response:
    assert isinstance(req.ctx.db, SomeDb)
    return html_response("ctx")


# return custom build response
@router.route("/custom_response_handler")
async def custom_response_handler(req: CtxRequest) -> Response:
    return Response(
        HTTPStatus.OK,
        headers_from_dict({"X-Value": "42"}),
        body="hello from custom_response",
        cookies=Cookies({"key": "value"}),
    )


# request headers
@router.route("/headers_handler")
async def headers_handler(req: CtxRequest) -> Response:
    value = req.headers.get("User-Agent")  # get header first value by name
    values = req.headers.get_all("User-Agent")  # get header all values by name

    assert isinstance(value, str) and len(value) > 0
    assert isinstance(values, list) and value in values

    return html_response("headers_handler")


# request headers
@router.route("/body_handler", ["POST"])
async def body_handler(req: CtxRequest) -> Response:
    body = await req.body()  # read body
    body.seek(0)
    data = body.read()

    data2 = await req.body_data()  # or get body content with Rquest.body_data()

    assert data == data2

    return html_response(data)


@router.route("/address_handler")
async def address_handler(req: CtxRequest) -> Response:
    return html_response(f"{req.address}")


@router.route("/method_handler")
async def method_handler(req: CtxRequest) -> Response:
    return html_response(f"{req.method}")


@router.route("/path_handler")
async def path_handler(req: CtxRequest) -> Response:
    return html_response(f"{req.path}")


# add routes with Router.add
router.add(SimpleRoute("/form_urlencoded_handler", form_urlencoded_handler, ["POST"]))
router.add(SimpleRoute("/multipart_form_handler", multipart_form_handler, ["POST"]))

router.add(
    SimpleRoute(
        "/other_sensitive_data_handler",
        # we can simply wrap any handler with any middleware
        basic_auth_middleware(other_sensitive_data_handler, "user", "pass"),
    )
)

# serve static directory
router.add(FileSystemRoute(os.path.dirname(__file__) + "/static_dir", "/static"))


# define common middlewares that wraps all handlers
def common_middleware1(call_next: CtxAsyncHandler) -> CtxAsyncHandler:
    async def f(req: CtxRequest) -> Response:
        print("hello from common_middleware1")
        resp = await call_next(req)
        print("bye from common_middleware1")
        return resp

    return f


# this middleware call after common_middleware1
# so we should get something like this
#
# hello from common_middleware1
#   hello from common_middleware2
#     ... some handler ...
#   bye from common_middleware2"
# bye from common_middleware1
def common_middleware2(call_next: CtxAsyncHandler) -> CtxAsyncHandler:
    async def f(req: CtxRequest) -> Response:
        print("  hello from common_middleware2")
        resp = await call_next(req)
        print("  bye from common_middleware2")
        return resp

    return f


async def before_server_start(ctx: Context):
    print("hello")
    await ctx.db.open()
    await ctx.cache.open()


async def after_server_stop(ctx: Context):
    await ctx.db.close()
    await ctx.cache.close()
    print("buy")


my_ctx = Context(SomeDb(), SomeCache())

s = Server(
    router,
    middlewares=[common_middleware1, common_middleware2],  # add common middlewares
    before_server_start=before_server_start,  # run this function before server start
    after_server_stop=after_server_stop,  # run this function after server start
    ctx=my_ctx,  # add application context
)
host = "127.0.0.1"
port = 8000

# run server
asyncio.run(s.run(host, port))
