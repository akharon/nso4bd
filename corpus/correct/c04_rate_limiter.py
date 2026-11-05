"""Token-bucket rate limiting."""

import time


class TokenBucket:
    def __init__(self, capacity_tokens, refill_per_second):
        self.capacity_tokens = capacity_tokens
        self.refill_per_second = refill_per_second
        self.tokens = float(capacity_tokens)
        self.last_refill_at = time.monotonic()

    def _refill(self, now_seconds):
        elapsed_seconds = now_seconds - self.last_refill_at
        minted = elapsed_seconds * self.refill_per_second
        self.tokens = min(self.capacity_tokens, self.tokens + minted)
        self.last_refill_at = now_seconds

    def try_consume(self, cost_tokens, now_seconds=None):
        now = time.monotonic() if now_seconds is None else now_seconds
        self._refill(now)
        if self.tokens < cost_tokens:
            return False
        self.tokens -= cost_tokens
        return True

    def seconds_until_available(self, cost_tokens, now_seconds=None):
        now = time.monotonic() if now_seconds is None else now_seconds
        self._refill(now)
        if self.tokens >= cost_tokens:
            return 0.0
        deficit_tokens = cost_tokens - self.tokens
        return deficit_tokens / self.refill_per_second
