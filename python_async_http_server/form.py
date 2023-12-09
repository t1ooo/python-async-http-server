import asyncio
from cgi import FieldStorage
from collections import defaultdict
from typing import IO, Any
from urllib.parse import parse_qs
from .headers import Headers

Form = dict[str, list[str]]
Files = list[FieldStorage]


def parse_form_urlencoded(data: str) -> Form:
    return parse_qs(data)


async def parse_multipart_form(
    headers: Headers,
    fp: IO[Any],
) -> tuple[Form, Files]:
    fs = await asyncio.to_thread(
        FieldStorage,
        fp,
        headers=headers,
        environ={"REQUEST_METHOD": "POST"},
    )

    form: Form = defaultdict(list)
    files: Files = []
    for k in fs:
        if fs[k].filename is None:
            form[fs[k].name].append(fs[k].value)
        else:
            files.append(fs[k])

    return dict(form), files
