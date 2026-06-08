"""Unit tests for the retry utility with exponential backoff."""

import time
from unittest.mock import patch

import pytest

from scripts.retry import with_retry


class TestWithRetry:
    """Tests for the with_retry decorator."""

    def test_succeeds_on_first_attempt(self):
        """Function that doesn't raise returns immediately."""
        call_count = 0

        @with_retry(max_retries=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_retries_on_retryable_exception(self):
        """Function retries on specified exceptions and eventually succeeds."""
        call_count = 0

        @with_retry(max_retries=3, backoff_base=0.01, retryable_exceptions=(ConnectionError,))
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("connection refused")
            return "recovered"

        result = fail_then_succeed()
        assert result == "recovered"
        assert call_count == 3

    def test_raises_after_all_retries_exhausted(self):
        """Raises last exception when all retries are exhausted."""
        call_count = 0

        @with_retry(max_retries=2, backoff_base=0.01, retryable_exceptions=(TimeoutError,))
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("timed out")

        with pytest.raises(TimeoutError, match="timed out"):
            always_fail()

        # Initial attempt + 2 retries = 3 total calls
        assert call_count == 3

    def test_does_not_retry_non_retryable_exceptions(self):
        """Non-retryable exceptions propagate immediately without retry."""
        call_count = 0

        @with_retry(max_retries=3, backoff_base=0.01, retryable_exceptions=(ConnectionError,))
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            raise_value_error()

        assert call_count == 1

    def test_exponential_backoff_delays(self):
        """Verifies exponential backoff timing: backoff_base * 2^attempt."""
        delays = []

        @with_retry(max_retries=3, backoff_base=1.0, retryable_exceptions=(ConnectionError,))
        def always_fail():
            raise ConnectionError("fail")

        with patch("scripts.retry.time.sleep") as mock_sleep:
            with pytest.raises(ConnectionError):
                always_fail()

            # Should have slept 3 times: 1*2^0=1, 1*2^1=2, 1*2^2=4
            assert mock_sleep.call_count == 3
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays == [1.0, 2.0, 4.0]

    def test_custom_backoff_base(self):
        """Custom backoff_base scales the delays correctly."""

        @with_retry(max_retries=3, backoff_base=0.5, retryable_exceptions=(ConnectionError,))
        def always_fail():
            raise ConnectionError("fail")

        with patch("scripts.retry.time.sleep") as mock_sleep:
            with pytest.raises(ConnectionError):
                always_fail()

            delays = [call.args[0] for call in mock_sleep.call_args_list]
            # 0.5*2^0=0.5, 0.5*2^1=1.0, 0.5*2^2=2.0
            assert delays == [0.5, 1.0, 2.0]

    def test_preserves_function_metadata(self):
        """Decorator preserves the wrapped function's name and docstring."""

        @with_retry()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_zero_retries_means_single_attempt(self):
        """With max_retries=0, function is called once with no retries."""
        call_count = 0

        @with_retry(max_retries=0, backoff_base=0.01, retryable_exceptions=(ConnectionError,))
        def fail_once():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        with pytest.raises(ConnectionError):
            fail_once()

        assert call_count == 1

    def test_multiple_retryable_exception_types(self):
        """Retries on any of the specified exception types."""
        call_count = 0

        @with_retry(
            max_retries=3,
            backoff_base=0.01,
            retryable_exceptions=(ConnectionError, TimeoutError, OSError),
        )
        def raise_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("conn error")
            elif call_count == 2:
                raise TimeoutError("timeout")
            elif call_count == 3:
                raise OSError("os error")
            return "success"

        result = raise_different_errors()
        assert result == "success"
        assert call_count == 4

    def test_passes_args_and_kwargs_correctly(self):
        """Arguments and keyword arguments are passed through to the function."""

        @with_retry(max_retries=1, backoff_base=0.01)
        def add(a, b, offset=0):
            return a + b + offset

        assert add(2, 3, offset=10) == 15
