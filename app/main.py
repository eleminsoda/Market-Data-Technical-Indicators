from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from app.config import settings
from app.indicators import bars_to_dataframe, build_technical_summary
from app.polygon_client import get_daily_bars
from app.schemas import TechnicalResponse


app = FastAPI(
    title="Market Technical API",
    version="0.1.0",
    description="Market technical analysis API for GPT-powered trading research.",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def verify_action_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    if not settings.action_api_key:
        return

    if x_api_key != settings.action_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@app.get(
    "/v1/market/technicals/{ticker}",
    response_model=TechnicalResponse,
    operation_id="getMarketTechnicals",
    summary="Get technical market summary",
    description=(
        "Fetch split-adjusted daily OHLCV data from Polygon and return a compact "
        "technical analysis summary for GPT stock research workflows."
    ),
)
async def get_market_technicals(
    ticker: str,
    days: int = Query(default=450, ge=80, le=1000),
    _: None = Depends(verify_action_api_key),
):
    try:
        bars, polygon_metadata = await get_daily_bars(ticker=ticker, days=days)
        df = bars_to_dataframe(bars)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No market data found for {ticker}")

        summary = build_technical_summary(df)

        return {
            "ticker": ticker.upper(),
            "adjusted": bool(polygon_metadata.get("adjusted", True)),
            "requested_lookback_days": days,
            "cache_hit": bool(polygon_metadata.get("cache_hit", False)),
            **summary,
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError as error:
        upstream_status = error.response.status_code
        if upstream_status == status.HTTP_429_TOO_MANY_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Polygon rate limit exceeded; retry later.",
            )

        if 400 <= upstream_status < 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Polygon rejected the market data request. Check ticker and parameters.",
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Polygon market data service returned an upstream error.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out while requesting Polygon market data.",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Polygon market data service.",
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
