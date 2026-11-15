"""Base62, SSRF guard, GDPR IP hashing, Redis Lua sliding-window limiter."""
import hashlib, ipaddress, logging, secrets, socket, time
from urllib.parse import urlparse
from app.core.config import settings

log = logging.getLogger("ls")

async def safe(coro, default=None):
    """Await a Redis call; on failure log and return default so the API stays up."""
    try:
        return await coro
    except Exception as e:
        log.warning("redis unavailable: %s", e)
        return default

ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def base62(n: int) -> str:
    out = ""
    while n:
        n, r = divmod(n, 62); out = ALPHA[r] + out
    return out or "0"

def new_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHA) for _ in range(length))

def hash_ip(ip: str) -> str:
    return hashlib.sha256((settings.ip_salt + ip).encode()).hexdigest()

def assert_public_url(url: str) -> str:
    """Reject non-http(s) and hosts resolving to private/loopback/link-local space (anti-SSRF)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only http(s) URLs allowed")
    for info in socket.getaddrinfo(p.hostname, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private address blocked")
    return url

LUA = """local k=KEYS[1];local now=tonumber(ARGV[1]);local w=tonumber(ARGV[2]);local l=tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE',k,0,now-w);if redis.call('ZCARD',k)>=l then return 0 end
redis.call('ZADD',k,now,now..math.random());redis.call('PEXPIRE',k,w);return 1"""

async def allow(redis, key: str, limit: int = 60, window_ms: int = 60000) -> bool:
    """Sliding-window check; fails open (allows) if Redis is down."""
    res = await safe(redis.eval(LUA, 1, f"rl:{key}", int(time.time() * 1000), window_ms, limit), 1)
    return bool(res)
