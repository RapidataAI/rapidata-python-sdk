from __future__ import annotations

import random

_MAX_DELAY_SECONDS = 30.0


def backoff_delay(attempt: int, base_delay: float = 1.0) -> float:
    """Exponential backoff with equal jitter, in seconds.

    The jitter is the point: without it, every worker that failed inside the
    same congestion window retries in lockstep and recreates the congestion
    that caused the failure. Half the delay is fixed so a retry still backs
    off meaningfully, half is random so the pool spreads out.
    """
    ceiling = min(base_delay * (2**attempt), _MAX_DELAY_SECONDS)
    half = ceiling / 2
    return half + random.uniform(0, half)
