"""Use routing if you want a single cohesive app where all routes share middlewares and error handling."""

from collections.abc import Callable, Sequence
from enum import Enum
from types import FunctionType
from typing import (
    Annotated,
    Any,
    Literal,
    override,
)
from warnings import deprecated

from fastapi import params
from fastapi.routing import APIRoute, APIRouter
from starlette.responses import Response
from starlette.routing import (
    BaseRoute,
)
from starlette.types import ASGIApp, Lifespan
from typing_extensions import Doc

from .decorator_utils import create_route_decorator
from .exception_handlers import default_404_router_handler
from .requests import AirRequest
from .responses import AirResponse
from .types import RouteCallable
from .utils import compute_page_path, default_generate_unique_id


class AirRoute(APIRoute):
    """Custom APIRoute that uses Air's custom AirRequest class."""

    @override
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Any) -> Response:
            request = AirRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler


class RouterMixin:
    path_separator: Literal["/", "-"]

    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Stub for type checking - implemented by subclasses."""
        raise NotImplementedError

    def url_path_for(self, name: str, **params: Any) -> str:
        """Stub for type checking - implemented by subclasses."""
        raise NotImplementedError

    def page(self, func: FunctionType) -> RouteCallable:
        """Decorator that creates a GET route using the function name as the path.

        If the name of the function is "index", then the route is "/".

        Example:

            import air

            app = air.Air()
            router = air.AirRouter()


            @app.page
            def index():  # route is "/"
                return air.H1("I am the home page")


            @router.page
            def data():  # route is "/data"
                return air.H1("I am the data page")


            @router.page
            def about_us():  # route is "/about-us"
                return air.H1("I am the about page")


            app.include_router(router)
        """
        page_path = compute_page_path(func.__name__, separator=self.path_separator)

        # Pin the route's response_class for belt-and-suspenders robustness
        return self.get(page_path)(func)

    def _url_helper(self, name: str) -> Callable[..., str]:
        """Helper function to generate URLs for route operations.

        Creates a callable that generates URLs for a specific route by wrapping
        Starlette's `url_path_for` method.

        Args:
            name: The route operation name (usually the function name or custom name).

        Returns:
            A function that accepts **params (path parameters) and returns the
            generated URL string.

        Raises:
            NoMatchFound: If the route name doesn't exist or if the provided parameters
                don't match the route's path parameters.

        Example:
            @app.get("/users/{user_id}")
            def get_user(user_id: int):
                return air.H1(f"User {user_id}")

            # The .url() method is created by this helper
            url = get_user.url(user_id=123)  # Returns: "/users/123"
        """

        def helper_function(**params: Any) -> str:
            return self.url_path_for(name, **params)

        return helper_function


class AirRouter(APIRouter, RouterMixin):
    """
    `AirRouter` class, used to group *path operations*, for example to structure
    an app in multiple files. It would then be included in the `App` app, or
    in another `AirRouter` (ultimately included in the app).

    Example

        ```python
        import air

        app = air.Air()
        router = air.AirRouter()


        @router.get("/users/", tags=["users"])
        async def read_users():
            return [{"username": "Rick"}, {"username": "Morty"}]


        app.include_router(router)
        ```
    """

    def __init__(
        self,
        *,
        prefix: Annotated[str, Doc("An optional path prefix for the router.")] = "",
        tags: Annotated[
            list[str | Enum] | None,
            Doc(
                """
                A list of tags to be applied to all the *path operations* in this
                router.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                Read more about it in the
                [FastAPI docs for Path Operation Configuration](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/).
                """
            ),
        ] = None,
        dependencies: Annotated[
            Sequence[params.Depends] | None,
            Doc(
                """
                A list of dependencies (using `Depends()`) to be applied to all the
                *path operations* in this router.

                Read more about it in the
                [FastAPI docs for Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/#include-an-apirouter-with-a-custom-prefix-tags-responses-and-dependencies).
                """
            ),
        ] = None,
        default_response_class: Annotated[
            type[Response],
            Doc(
                """
                The default response class to be used.

                Read more in the
                [FastAPI docs for Custom Response - HTML, Stream, File, others](https://fastapi.tiangolo.com/advanced/custom-response/#default-response-class).
                """
            ),
        ] = AirResponse,
        responses: Annotated[
            dict[int | str, dict[str, Any]] | None,
            Doc(
                """
                Additional responses to be shown in OpenAPI.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                Read more about it in the
                [FastAPI docs for Additional Responses in OpenAPI](https://fastapi.tiangolo.com/advanced/additional-responses/).

                And in the
                [FastAPI docs for Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/#include-an-apirouter-with-a-custom-prefix-tags-responses-and-dependencies).
                """
            ),
        ] = None,
        callbacks: Annotated[
            list[BaseRoute] | None,
            Doc(
                """
                OpenAPI callbacks that should apply to all *path operations* in this
                router.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                Read more about it in the
                [FastAPI docs for OpenAPI Callbacks](https://fastapi.tiangolo.com/advanced/openapi-callbacks/).
                """
            ),
        ] = None,
        routes: Annotated[
            list[BaseRoute] | None,
            Doc(
                """
                **Note**: you probably shouldn't use this parameter, it is inherited
                from Starlette and supported for compatibility.

                ---

                A list of routes to serve incoming HTTP and WebSocket requests.
                """
            ),
            deprecated(
                """
                You normally wouldn't use this parameter with FastAPI, it is inherited
                from Starlette and supported for compatibility.

                In FastAPI, you normally would use the *path operation methods*,
                like `router.get()`, `router.post()`, etc.
                """
            ),
        ] = None,
        redirect_slashes: Annotated[
            bool,
            Doc(
                """
                Whether to detect and redirect slashes in URLs when the client doesn't
                use the same format.
                """
            ),
        ] = True,
        default: Annotated[
            ASGIApp | None,
            Doc(
                """
                Default function handler for this router. Used to handle
                404 Not Found errors.
                """
            ),
        ] = None,
        dependency_overrides_provider: Annotated[
            Any | None,
            Doc(
                """
                Only used internally by FastAPI to handle dependency overrides.

                You shouldn't need to use it. It normally points to the `FastAPI` app
                object.
                """
            ),
        ] = None,
        route_class: Annotated[
            type[AirRoute],
            Doc(
                """
                Custom route (*path operation*) class to be used by this router.

                Read more about it in the
                [FastAPI docs for Custom Request and APIRoute class](https://fastapi.tiangolo.com/how-to/custom-request-and-route/#custom-apiroute-class-in-a-router).
                """
            ),
        ] = AirRoute,
        on_startup: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of startup event handler functions.

                You should instead use the `lifespan` handlers.

                Read more in the [FastAPI docs for `lifespan`](https://fastapi.tiangolo.com/advanced/events/).
                """
            ),
        ] = None,
        on_shutdown: Annotated[
            Sequence[Callable[[], Any]] | None,
            Doc(
                """
                A list of shutdown event handler functions.

                You should instead use the `lifespan` handlers.

                Read more in the
                [FastAPI docs for `lifespan`](https://fastapi.tiangolo.com/advanced/events/).
                """
            ),
        ] = None,
        # the generic to Lifespan[AppType] is the type of the top level application
        # which the router cannot know statically, so we use typing.Any
        lifespan: Annotated[
            Lifespan[Any] | None,  # ty: ignore[invalid-type-form]
            Doc(
                """
                A `Lifespan` context manager handler. This replaces `startup` and
                `shutdown` functions with a single context manager.

                Read more in the
                [FastAPI docs for `lifespan`](https://fastapi.tiangolo.com/advanced/events/).
                """
            ),
        ] = None,
        deprecated: Annotated[
            bool | None,
            Doc(
                """
                Mark all *path operations* in this router as deprecated.

                It will be added to the generated OpenAPI (e.g. visible at `/docs`).

                Read more about it in the
                [FastAPI docs for Path Operation Configuration](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/).
                """
            ),
        ] = None,
        include_in_schema: Annotated[
            bool,
            Doc(
                """
                To include (or not) all the *path operations* in this router in the
                generated OpenAPI.

                This affects the generated OpenAPI (e.g. visible at `/docs`).

                Read more about it in the
                [FastAPI docs for Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#exclude-parameters-from-openapi).
                """
            ),
        ] = True,
        generate_unique_id_function: Annotated[
            Callable[[APIRoute], str],
            Doc(
                """
                Customize the function used to generate unique IDs for the *path
                operations* shown in the generated OpenAPI.

                This is particularly useful when automatically generating clients or
                SDKs for your API.

                Read more about it in the
                [FastAPI docs about how to Generate Clients](https://fastapi.tiangolo.com/advanced/generate-clients/#custom-generate-unique-id-function).
                """
            ),
        ] = default_generate_unique_id,
        path_separator: Annotated[Literal["/", "-"], Doc("An optional path separator.")] = "-",
    ) -> None:
        self.path_separator = path_separator
        if default is None:
            default = default_404_router_handler(prefix or "router")
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            generate_unique_id_function=generate_unique_id_function,
        )
        if prefix:
            assert prefix.startswith("/"), "A path prefix must start with '/'"
            assert not prefix.endswith("/"), "A path prefix must not end with '/' except for the root path"

    get = create_route_decorator("get")
    post = create_route_decorator("post")
    patch = create_route_decorator("patch")
    put = create_route_decorator("put")
    delete = create_route_decorator("delete")
