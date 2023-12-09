import datetime

_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %Z"
_TZ = datetime.timezone(datetime.timedelta(0), name="GMT")


def http_date_now():
    dt = datetime.datetime.now(_TZ)
    return dt.strftime(_DATE_FORMAT)


def http_date_from_timestamp(ts: float) -> str:
    dt = datetime.datetime.fromtimestamp(ts, _TZ)
    return dt.strftime(_DATE_FORMAT)
