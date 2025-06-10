import typing

from velithon.datastructures import Headers, Protocol, Scope
from velithon.middleware.base import ConditionalMiddleware
from velithon.responses import PlainTextResponse, Response

ALL_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")
SAFELISTED_HEADERS = {"Accept", "Accept-Language", "Content-Language", "Content-Type"}


class CORSMiddleware(ConditionalMiddleware):
    def __init__(
        self,
        app: typing.Any,
        allow_origins: typing.Sequence[str] = (),
        allow_methods: typing.Sequence[str] = ("GET",),
        allow_headers: typing.Sequence[str] = (),
        allow_credentials: bool = False,
        max_age: int = 600,
    ) -> None:
        super().__init__(app)

        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        allow_all_origins = "*" in allow_origins
        allow_all_headers = "*" in allow_headers
        preflight_explicit_allow_origin = not allow_all_origins or allow_credentials

        simple_headers = []
        if allow_all_origins:
            simple_headers.append(("Access-Control-Allow-Origin", "*"))
        if allow_credentials:
            simple_headers.append(("Access-Control-Allow-Credentials", "true"))

        preflight_headers = []
        if preflight_explicit_allow_origin:
            preflight_headers.append(("vary", "Origin"))
        else:
            preflight_headers.append(("Access-Control-Allow-Origin", "*"))

        preflight_headers.extend(
            [
                ("Access-Control-Allow-Methods", ", ".join(allow_methods)),
                ("Access-Control-Max-Age", str(max_age)),
            ]
        )

        allow_headers = sorted(SAFELISTED_HEADERS | set(allow_headers))
        if allow_headers and not allow_all_headers:
            preflight_headers.append(
                ("Access-Control-Allow-Headers", ", ".join(allow_headers))
            )
        if allow_credentials:
            preflight_headers.append(("Access-Control-Allow-Credentials", "true"))

        self.allow_methods = allow_methods
        self.allow_headers = [h.lower() for h in allow_headers]
        self.allow_all_headers = allow_all_headers
        self.allow_all_origins = allow_all_origins
        self.allow_origins = allow_origins
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        self.allow_origin_regex = None  # For potential future regex support
        self.preflight_explicit_allow_origin = preflight_explicit_allow_origin
        self.simple_headers = simple_headers
        self.preflight_headers = preflight_headers

    async def should_process_request(self, scope: Scope, protocol: Protocol) -> bool:
        """Handle CORS logic and return whether to continue processing."""
        header = scope.headers
        if scope.method == "OPTIONS":
            # Handle preflight request
            response = self.preflight_response(header)
            await response(scope, protocol)
            return False  # Don't continue processing
        else:
            # Handle simple request
            protocol.update_headers(self.simple_headers)
            return True  # Continue processing

    def is_allowed_origin(self, origin: str) -> bool:
        if self.allow_all_origins:
            return True

        if self.allow_origin_regex is not None and self.allow_origin_regex.fullmatch(
            origin
        ):
            return True

        return origin in self.allow_origins

    def preflight_response(self, request_headers: Headers) -> Response:
        requested_origin = request_headers.get("origin") or ""
        requested_method = request_headers.get("access-control-request-method") or ""
        requested_headers = request_headers.get("access-control-request-headers") or ""

        headers = dict(self.preflight_headers)
        headers["Access-Control-Allow-Origin"] = requested_origin
        failures = []

        if requested_method not in self.allow_methods:
            failures.append("method")

        # If we allow all headers, then we have to mirror back any requested
        # headers in the response.
        if self.allow_all_headers and requested_headers is not None:
            headers["Access-Control-Allow-Headers"] = requested_headers
        elif requested_headers is not None:
            for header in [h.lower() for h in requested_headers.split(",")]:
                if header.strip() not in self.allow_headers:
                    failures.append("headers")
                    break

        # We don't strictly need to use 400 responses here, since its up to
        # the browser to enforce the CORS policy, but its more informative
        # if we do.
        if failures:
            failure_text = "Disallowed CORS " + ", ".join(failures)
            return PlainTextResponse(failure_text, status_code=400, headers=headers)

        return PlainTextResponse("OK", status_code=200, headers=headers)
