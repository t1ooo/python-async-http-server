from pathlib import Path

PathParams = dict[str, str]


def has_path_params(pattern: str) -> bool:
    return "/:" in pattern


def extract_path_params(pattern: str, path: str) -> PathParams | None:
    pattern_p = Path(pattern).parts
    path_p = Path(path).parts

    params: PathParams = {}
    if len(pattern_p) != len(path_p):
        return None
    for r, u in zip(pattern_p, path_p):
        if r.startswith(":"):
            params[r[1:]] = u
            continue
        if r != u:
            return None

    return PathParams(params)
