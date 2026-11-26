"""Per-key sliding-window rate limiting shared across workers."""
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from .config import settings
from .redis_client import r

WINDOW_SECONDS = 60

# Prune, check and record atomically. Redis time keeps workers on the same clock.
_record_request = r.register_script("""
local bucket = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', bucket, '-inf', now - window)
if redis.call('ZCARD', bucket) >= limit then
    local oldest = redis.call('ZRANGE', bucket, 0, 0, 'WITHSCORES')
    if #oldest == 0 then
        return window
    end
    return math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
end
redis.call('ZADD', bucket, now, ARGV[3])
redis.call('EXPIRE', bucket, window)
return 0
""")


def check_rate_limit(key: str) -> None:
    bucket = f"day14:rate:{sha256(key.encode()).hexdigest()}"
    retry_after = _record_request(
        keys=[bucket],
        args=[settings.rate_limit_per_minute, WINDOW_SECONDS, uuid4().hex],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
