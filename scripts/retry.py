"""Retry utility with exponential backoff for transient failure handling.

Provides a decorator for retrying operations that may fail due to transient
issues such as database connection errors or file I/O timeouts.

Usage:
    from scripts.retry import with_retry

    @with_retry(max_retries=3, backoff_base=1.0, retryable_exceptions=(ConnectionError, TimeoutError))
    def connect_to_database():
        ...
"""

import time
from functools import wraps
from typing import Callable, TypeVar

from scripts.logging_config import get_logger

T = TypeVar("T")

logger = get_logger("retry")


def with_retry(
    max_retries: int = 3,
    backoff_base: float = 1.0,
    retryable_exceptions: tuple = (ConnectionError, TimeoutError),
) -> Callable:
    """Decorator for retry with exponential backoff.

    Retries the decorated function on specified transient exceptions using
    exponential backoff: backoff_base * 2^attempt seconds between attempts.

    Default delays: 1s, 2s, 4s (for backoff_base=1.0 and max_retries=3).

    Args:
        max_retries: Maximum number of retry attempts. Defaults to 3.
        backoff_base: Base delay in seconds for exponential backoff. Defaults to 1.0.
        retryable_exceptions: Tuple of exception types that trigger a retry.
            Defaults to (ConnectionError, TimeoutError).

    Returns:
        A decorator that wraps a function with retry logic.

    Raises:
        The last exception encountered if all retries are exhausted.

    Example:
        @with_retry(max_retries=3, backoff_base=1.0)
        def fetch_data():
            # May raise ConnectionError on transient network issues
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: BaseException | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc

                    if attempt < max_retries:
                        delay = backoff_base * (2**attempt)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {exc}",
                            extra={
                                "context": {
                                    "function": func.__name__,
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries,
                                    "delay_seconds": delay,
                                    "exception_type": type(exc).__name__,
                                    "exception_message": str(exc),
                                }
                            },
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}: {exc}",
                            extra={
                                "context": {
                                    "function": func.__name__,
                                    "max_retries": max_retries,
                                    "exception_type": type(exc).__name__,
                                    "exception_message": str(exc),
                                }
                            },
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
