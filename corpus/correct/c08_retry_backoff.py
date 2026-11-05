"""Retry loop with exponential backoff."""

import random


class RetryExhausted(Exception):
    pass


def backoff_delay_seconds(attempt, base_delay_seconds, max_delay_seconds):
    raw = base_delay_seconds * (2 ** attempt)
    capped = min(raw, max_delay_seconds)
    return capped * (0.5 + random.random() / 2.0)


def call_with_retry(operation, max_attempts, base_delay_seconds,
                    max_delay_seconds, sleeper):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return operation()
        except TransientError as exc:
            last_error = exc
            if attempt == max_attempts - 1:
                break
            sleeper(backoff_delay_seconds(
                attempt, base_delay_seconds, max_delay_seconds))
    raise RetryExhausted(str(last_error))


class TransientError(Exception):
    pass
