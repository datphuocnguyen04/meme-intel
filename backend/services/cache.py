import time
import asyncio
from typing import Any, Optional, Dict


class InMemoryTTLCache:
    """
    High-performance, in-memory TTL Cache leveraging your system's 64GB RAM.
    Stores precomputed results with automatic expiration.
    """

    def __init__(self, default_ttl_seconds: int = 600, max_items: int = 10000):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl_seconds
        self._max_items = max_items
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        async with self._lock:
            if key in self._cache:
                data, expiry = self._cache[key]
                if now < expiry:
                    self.hits += 1
                    return data
                else:
                    # Expired — remove from RAM
                    del self._cache[key]
            self.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.monotonic() + ttl
        async with self._lock:
            # Prevent unbounded growth
            if len(self._cache) >= self._max_items:
                # Remove expired keys first
                now = time.monotonic()
                expired_keys = [k for k, (_, exp) in self._cache.items() if exp <= now]
                for k in expired_keys:
                    del self._cache[k]
                # If still full, pop oldest 10%
                if len(self._cache) >= self._max_items:
                    keys_to_remove = list(self._cache.keys())[: max(1, self._max_items // 10)]
                    for k in keys_to_remove:
                        del self._cache[k]

            self._cache[key] = (value, expiry)

    async def clear(self):
        async with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


# 1. Price & Market Metrics Cache: 10-second TTL
# Keeps prices fresh while eliminating duplicate DexScreener spikes
price_cache = InMemoryTTLCache(default_ttl_seconds=10, max_items=20000)

# 2. AI Narrative & Tweets Cache: 10-minute (600s) TTL
# Eliminates redundant Gemini and SocialData calls for the same token
analysis_cache = InMemoryTTLCache(default_ttl_seconds=600, max_items=20000)
