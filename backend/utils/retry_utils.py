"""Retry utilities with exponential backoff."""

import random
from dataclasses import dataclass
from typing import TypeVar, Callable, Awaitable
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    RetryError,
)

from settings.config import get_settings

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 1.0
    retryable_exceptions: tuple = (Exception,)


def get_default_retry_config() -> RetryConfig:
    """Get retry config from settings."""
    settings = get_settings()
    return RetryConfig(
        max_attempts=settings.retry_max_attempts,
        base_delay=settings.retry_base_delay,
    )


def with_retry(
    config: RetryConfig | None = None,
    retryable_exceptions: tuple | None = None,
):
    """
    Decorator for adding retry logic with exponential backoff and jitter.

    Args:
        config: Retry configuration (uses defaults if not provided)
        retryable_exceptions: Exception types to retry on

    Usage:
        @with_retry()
        async def my_flaky_function():
            ...

        @with_retry(RetryConfig(max_attempts=5))
        async def another_function():
            ...
    """
    if config is None:
        config = get_default_retry_config()

    exceptions = retryable_exceptions or config.retryable_exceptions

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @retry(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential_jitter(
                initial=config.base_delay,
                max=config.max_delay,
                jitter=config.jitter,
            ),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def retry_operation(
    operation: Callable[..., Awaitable[T]],
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> T:
    """
    Execute an operation with retry logic.

    Args:
        operation: Async function to execute
        *args: Positional arguments for operation
        config: Retry configuration
        **kwargs: Keyword arguments for operation

    Returns:
        Result of the operation

    Raises:
        RetryError: If all retries are exhausted
    """
    if config is None:
        config = get_default_retry_config()

    @retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential_jitter(
            initial=config.base_delay,
            max=config.max_delay,
            jitter=config.jitter,
        ),
        reraise=True,
    )
    async def _execute():
        return await operation(*args, **kwargs)

    return await _execute()
