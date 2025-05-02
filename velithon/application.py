from typing import Annotated, Any, Callable, Dict, List, Sequence, TypeVar

from typing_extensions import Doc

from velithon.middleware import Middleware
from velithon.routing import BaseRoute, Router
from velithon.types import Protocol, RSGIApp, Scope

AppType = TypeVar("AppType", bound="Velithon")


class Velithon:
    def __init__(
        self: AppType,
        *,
        debug: Annotated[
            bool,
            Doc(
                """
                Boolean indicating if debug tracebacks should be returned on server
                errors.
                """
            ),
        ] = False,
        routes: Annotated[
            Sequence[BaseRoute] | None,
            Doc(
                """
                A list of routes to be registered with the application. If not
                provided, the application will not have any routes.
                """
            ),
        ] = None,
        middleware: Annotated[
            Sequence[Middleware] | None,
            Doc(
                """
                A list of middleware classes to be applied to the application. If
                not provided, no middleware will be applied.
                """
            ),
        ] = None,
        on_startup: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of callables to be executed on application startup. If not
                provided, no startup actions will be performed.
                """
            ),
        ] = None,
        on_shutdown: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of callables to be executed on application shutdown. If not
                provided, no shutdown actions will be performed.
                """
            ),
        ] = None,
        title: Annotated[
            str,
            Doc(
                """
                The title of the application. This is used for documentation
                generation and other purposes.
                """
            ),
        ] = "Velithon",
        summary: Annotated[
            str | None,
            Doc(
                """
                A short summary of the API.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
        description: Annotated[
            str,
            Doc(
                """
                A description of the API. Supports Markdown (using
                [CommonMark syntax](https://commonmark.org/)).

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = "",
        version: Annotated[
            str,
            Doc(
                """
                The version of the API.

                **Note** This is the version of your application, not the version of
                the OpenAPI specification nor the version of App being used.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                """
            ),
        ] = "0.1.0",
        openapi_url: Annotated[
            str | None,
            Doc(
                """
                The URL where the OpenAPI schema will be served from.

                If you set it to `None`, no OpenAPI schema will be served publicly, and
                the default automatic endpoints `/docs` and `/redoc` will also be
                disabled.

                """
            ),
        ] = "/openapi.json",
        openapi_tags: Annotated[
            List[Dict[str, Any]] | None,
            Doc(
                """
                A list of tags used by OpenAPI, these are the same `tags` you can set
                in the *path operations*, like:

                * `@app.get("/users/", tags=["users"])`
                * `@app.get("/items/", tags=["items"])`

                The order of the tags can be used to specify the order shown in
                tools like Swagger UI, used in the automatic path `/docs`.

                It's not required to specify all the tags used.

                The tags that are not declared MAY be organized randomly or based
                on the tools' logic. Each tag name in the list MUST be unique.

                The value of each item is a `dict` containing:
                """
            ),
        ] = None,
        servers: Annotated[
            List[Dict[str, str | Any]] | None,
            Doc(
                """
                A `list` of `dict`s with connectivity information to a target server.
                """
            ),
        ] = None,
        docs_url: Annotated[
            str | None,
            Doc(
                """
                The path to the automatic interactive API documentation.
                It is handled in the browser by Swagger UI.

                The default URL is `/docs`. You can disable it by setting it to `None`.
                If `openapi_url` is set to `None`, this will be automatically disabled.
                """
            ),
        ] = "/docs",
        terms_of_service: Annotated[
            str | None,
            Doc(
                """
                A URL to the Terms of Service for your API.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                """
            ),
        ] = None,
        contact: Annotated[
            Dict[str, str | Any] | None,
            Doc(
                """
                A dictionary with the contact information for the exposed API.

                It can contain several fields.

                * `name`: (`str`) The name of the contact person/organization.
                * `url`: (`str`) A URL pointing to the contact information. MUST be in
                    the format of a URL.
                * `email`: (`str`) The email address of the contact person/organization.
                    MUST be in the format of an email address.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
        license_info: Annotated[
            Dict[str, str | Any] | None,
            Doc(
                """
                A dictionary with the license information for the exposed API.

                It can contain several fields.

                * `name`: (`str`) **REQUIRED** (if a `license_info` is set). The
                    license name used for the API.
                * `identifier`: (`str`) An [SPDX](https://spdx.dev/) license expression
                    for the API. The `identifier` field is mutually exclusive of the `url`
                    field
                * `url`: (`str`) A URL to the license used for the API. This MUST be
                    the format of a URL.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).
                """
            ),
        ] = None,
    ):
        self.debug = debug
        self.router = Router(routes, on_startup=on_startup, on_shutdown=on_shutdown)
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: RSGIApp | None = None
        self.title = title
        self.summary = summary
        self.description = description
        self.version = version
        self.openapi_url = openapi_url
        self.openapi_tags = openapi_tags
        self.servers = servers
        self.docs_url = docs_url
        self.terms_of_service = terms_of_service
        self.contact = contact
        self.license_info = license_info

    def build_middleware_stack(self) -> RSGIApp:
        middleware = self.user_middleware
        app = self.router
        for cls, args, kwargs in reversed(middleware):
            app = cls(app, *args, **kwargs)
        return app

    async def __call__(self, scope: Scope, protocol: Protocol):
        if self.middleware_stack is None:
            self.middleware_stack = self.build_middleware_stack()
        await self.middleware_stack(scope, protocol)

    def openapi(self) -> Dict[str, Any]:
        """
        Generate the OpenAPI schema for the application.
        """
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
                "termsOfService": self.terms_of_service,
                "contact": self.contact,
                "license": self.license_info,
            },
            "servers": self.servers,
            "tags": self.openapi_tags,
        }