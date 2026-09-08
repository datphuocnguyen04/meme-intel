import httpx
from typing import Optional

_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get or initialize the shared singleton httpx.AsyncClient with connection pooling.
    Reuses open TCP/SSL connections across DexScreener, GoPlus, and SocialData API calls.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=50,
            keepalive_expiry=30.0,
        )
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        _http_client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MemecoinIntel/2.0"},
        )
    return _http_client


async def close_http_client():
    """Gracefully close the pooled client on application shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None
