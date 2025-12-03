from collections.abc import Awaitable, Callable
from typing import Any, Protocol


type MaybeAwaitable[T] = T | Awaitable[T]


class RouteCallable(Protocol):
    """Protocol for route functions.

    This protocol represents the interface of functions after being decorated
    by route decorators like @app.get(), @app.post(), or @app.page(). The decorator
    adds a .url() method to the function, allowing programmatic URL generation.

    Example:
        @app.get("/users/{user_id}")
        def get_user(user_id: int) -> air.H1:
            return air.H1(f"User {user_id}")

        # The decorated function now has a .url() method
        url = get_user.url(user_id=123)  # Returns: "/users/123"
    """

    __call__: Callable[..., Any]
    __name__: str

    def url(self, **path_params: Any) -> str:
        return ""
