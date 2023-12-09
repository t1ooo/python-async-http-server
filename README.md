Async http server without any third party dependencies.

Features:
+ no third party dependencies (except testing)
+ fully typed
+ async
+ routing
    + simple path (like `/hello`)
    + path with parameters (`/person/:person/item/:item`)
    + decorators
+ middlewares
    + common for all handlers
    + for single handler
    + builtin middlewares
        + basic auth
+ url query params
+ request/response cookies
+ json request/response
+ forms
    + application/x-www-form-urlencoded
    + multipart/form-data
+ file upload
+ file download
+ serve static files
+ redirects
+ builtin response helpers
+ listeners
    + before_server_start
    + after_server_stop
+ type safe application context


See for examples `examples/example_server.py`.

Tags: python, async, http server, routing, forms
