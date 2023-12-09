from functools import partial
import os
from typing import Generic, Protocol
from urllib.parse import urlparse
from .context import Ctx
from .handler import AsyncHandler, handle_static_files
from .path_params import PathParams, extract_path_params, has_path_params


class Route(Protocol, Generic[Ctx]):
    pattern: str
    path_params: PathParams
    handler: AsyncHandler[Ctx]
    methods: list[str]

    def match(self, path: str, method: str) -> bool:
        ...


class SimpleRoute(Route[Ctx]):
    """like `/simple/path/`"""

    def __init__(
        self, pattern: str, handler: AsyncHandler[Ctx], methods: list[str] | None = None
    ):
        self.pattern = _validate_path(_prepare_path(pattern))
        self.methods = [_validate_method(m) for m in methods or ["GET"]]
        self.handler = handler
        self.path_params = {}

    def match(self, path: str, method: str) -> bool:
        return self.pattern == path and method in self.methods


class PathParamsRoute(Route[Ctx]):
    """like `/person/:person/item/:item`"""

    def __init__(
        self, pattern: str, handler: AsyncHandler[Ctx], methods: list[str] | None = None
    ):
        pattern = _validate_path(_prepare_path(pattern))
        if not has_path_params(pattern):
            raise Exception("path parameters not found in : {pattern}")

        self.pattern = pattern
        self.methods = [_validate_method(m) for m in methods or ["GET"]]
        self.handler = handler
        self.path_params: PathParams = {}

    def match(self, path: str, method: str) -> bool:
        self.path_params.clear()

        if method not in self.methods:
            return False
        params = extract_path_params(self.pattern, path)
        if params == None:
            return False

        self.path_params = params
        return True


class FileSystemRoute(Route[Ctx]):
    """like `/file/system/dir/`"""

    # TODO: support files
    def __init__(self, directory_path: str, pattern: str):
        if not os.path.isdir(directory_path):
            raise Exception(f"not a directory: {directory_path}")

        if not os.access(directory_path, os.R_OK):
            raise Exception(f"folder is not readable: {directory_path}")

        self.pattern = _validate_path(_prepare_path(pattern))
        self.methods = [_validate_method(m) for m in ["GET"]]
        self.handler = partial(handle_static_files, directory_path, pattern)
        self.path_params = {}

    def match(self, path: str, method: str) -> bool:
        return path.startswith(self.pattern) and method in self.methods


class Router(Generic[Ctx]):
    def __init__(self, routes: list[Route[Ctx]] | None = None):
        self.routes: dict[str, Route[Ctx]] = {}
        for route in routes or []:
            self.add(route)

    def add(self, route: Route[Ctx]):
        key = "-".join([route.pattern] + sorted(set(route.methods)))
        if key in self.routes:
            raise Exception(f"duplicate route: {key}")
        self.routes[key] = route

    def match(self, path: str, method: str) -> Route[Ctx] | None:
        path = _prepare_path(urlparse(path).path)

        for route in self.routes.values():
            if route.match(path, method):
                return route
        return None

    def route(self, path: str, methods: list[str] | None = None):
        cls = PathParamsRoute[Ctx] if has_path_params(path) else SimpleRoute[Ctx]

        def wrapper(h: AsyncHandler[Ctx]) -> AsyncHandler[Ctx]:
            route = cls(path, h, methods)
            self.add(route)
            return h

        return wrapper


def _validate_method(method: str) -> str:
    if method not in [
        "CONNECT",
        "DELETE",
        "GET",
        "HEAD",
        "OPTIONS",
        "PATCH",
        "POST",
        "PUT",
        "TRACE",
    ]:
        raise Exception(f"invalid method: {method}")
    return method


def _validate_path(path: str) -> str:
    if not path.startswith("/"):
        raise Exception(f"invalid path: {path}")
    return path


def _prepare_path(path: str) -> str:
    return path.rstrip("/")
