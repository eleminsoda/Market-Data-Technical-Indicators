from datetime import date, timedelta
from typing import Any

import httpx

from app.config import settings


POLYGON_BASE_URL = "https://api.polygon.io"


async def get_daily_bars(
    ticker: str,
    days: int = 400,
    adjusted: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch daily OHLCV bars from Polygon.
    We fetch ~400 calendar days so we have enough trading days for SMA 200.
    """
    end = date.today()
    start = end - timedelta(days=days)

    url = (
        f"{POLYGON_BASE_URL}/v2/aggs/ticker/{ticker.upper()}"
        f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
    )

    params = {
        "adjusted": str(adjusted).lower(),
        "sort": "asc",
        "limit": 50000,
        "apiKey": settings.polygon_api_key,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    return data.get("results", [])