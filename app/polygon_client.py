import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.config import settings


MAX_RETRIES = 2

_cache: dict[tuple[str, int, bool], tuple[datetime, list[dict[str, Any]], dict[str, Any]]] = {}


async def get_daily_bars(
    ticker: str,
    days: int = 400,
    adjusted: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Fetch daily OHLCV bars from Polygon.
    We fetch ~400 calendar days so we have enough trading days for SMA 200.
    """
    cache_key = (ticker.upper(), days, adjusted)
    now = datetime.now(UTC)
    _delete_expired_cache_entries(now)

    cached = _cache.get(cache_key)
    if cached:
        cached_at, cached_bars, cached_metadata = cached
        if (now - cached_at).total_seconds() < settings.market_cache_ttl_seconds:
            return cached_bars, {**cached_metadata, "cache_hit": True}

    end = date.today()
    start = end - timedelta(days=days)

    url = (
        f"{settings.polygon_base_url.rstrip('/')}/v2/aggs/ticker/{ticker.upper()}"
        f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
    )

    params = {
        "adjusted": str(adjusted).lower(),
        "sort": "asc",
        "limit": 50000,
        "apiKey": settings.polygon_api_key,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        for attempt in range(MAX_RETRIES + 1):
            response = await client.get(url, params=params)
            should_retry = response.status_code == 429 or response.status_code >= 500

            if should_retry and attempt < MAX_RETRIES:
                await asyncio.sleep(_retry_delay_seconds(response, attempt))
                continue

            response.raise_for_status()
            data = response.json()
            break

    metadata = {
        "adjusted": data.get("adjusted", adjusted),
        "request_id": data.get("request_id"),
        "status": data.get("status"),
        "query_count": data.get("queryCount"),
        "results_count": data.get("resultsCount"),
        "cache_hit": False,
    }

    bars = data.get("results", [])
    _cache[cache_key] = (datetime.now(UTC), bars, metadata)

    return bars, metadata


def clear_cache() -> None:
    _cache.clear()


def _delete_expired_cache_entries(now: datetime) -> None:
    expired_keys = [
        cache_key
        for cache_key, (cached_at, _, _) in _cache.items()
        if (now - cached_at).total_seconds() >= settings.market_cache_ttl_seconds
    ]

    for cache_key in expired_keys:
        del _cache[cache_key]


def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 5.0)
        except ValueError:
            pass

    return 0.5 * (2**attempt)
