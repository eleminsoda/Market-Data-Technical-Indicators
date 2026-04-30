from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, status

from app.config import settings
from app.indicators import bars_to_dataframe, build_technical_summary
from app.polygon_client import get_daily_bars
from app.schemas import TechnicalBatchRequest, TechnicalBatchResponse, TechnicalResponse


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


async def build_market_technicals_response(ticker: str, days: int) -> dict[str, Any]:
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise HTTPException(status_code=422, detail="Ticker must not be empty")

    bars, polygon_metadata = await get_daily_bars(ticker=normalized_ticker, days=days)
    df = bars_to_dataframe(bars)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No market data found for {normalized_ticker}")

    summary = build_technical_summary(df)

    return {
        "ticker": normalized_ticker,
        "adjusted": bool(polygon_metadata.get("adjusted", True)),
        "requested_lookback_days": days,
        "cache_hit": bool(polygon_metadata.get("cache_hit", False)),
        **summary,
    }


def market_error_to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, HTTPException):
        return error

    if isinstance(error, httpx.HTTPStatusError):
        upstream_status = error.response.status_code
        if upstream_status == status.HTTP_429_TOO_MANY_REQUESTS:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Market data provider rate limit exceeded; retry later.",
            )

        if 400 <= upstream_status < 500:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Market data provider rejected the request. Check ticker and parameters.",
            )

        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market data provider returned an upstream error.",
        )

    if isinstance(error, httpx.TimeoutException):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out while requesting market data.",
        )

    if isinstance(error, httpx.RequestError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach market data provider.",
        )

    if isinstance(error, ValueError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))

    return HTTPException(status_code=500, detail=str(error))


@app.post(
    "/v1/market/technicals/batch",
    response_model=TechnicalBatchResponse,
    operation_id="getBatchStockTechnicals",
    summary="Get batch stock technicals",
    description=(
        "Returns RSI, MACD, moving averages, volume, support/resistance, "
        "52-week levels, recent candles, warnings, and summaries for stock tickers."
    ),
)
async def get_batch_market_technicals(
    request: TechnicalBatchRequest,
    _: None = Depends(verify_action_api_key),
):
    results = []
    errors = []
    seen_tickers = set()

    for ticker in request.tickers:
        normalized_ticker = ticker.strip().upper()
        if normalized_ticker in seen_tickers:
            continue
        seen_tickers.add(normalized_ticker)

        try:
            results.append(
                await build_market_technicals_response(
                    ticker=normalized_ticker,
                    days=request.days,
                )
            )
        except Exception as error:
            http_error = market_error_to_http_exception(error)
            errors.append(
                {
                    "ticker": normalized_ticker or ticker,
                    "status_code": http_error.status_code,
                    "detail": str(http_error.detail),
                }
            )

    return {
        "requested_count": len(request.tickers),
        "returned_count": len(results),
        "results": results,
        "errors": errors,
    }


@app.get(
    "/v1/market/technicals/{ticker}",
    response_model=TechnicalResponse,
    operation_id="getStockTechnicals",
    summary="Get stock technicals",
    description=(
        "Returns RSI, MACD, moving averages, volume, support/resistance, "
        "52-week levels, recent candles, warnings, and a summary for one stock ticker."
    ),
)
async def get_market_technicals(
    ticker: str = Path(description="Stock ticker to analyze."),
    days: int = Query(
        default=450,
        ge=80,
        le=1000,
        description="Calendar-day lookback used to fetch daily bars.",
    ),
    _: None = Depends(verify_action_api_key),
):
    try:
        return await build_market_technicals_response(ticker=ticker, days=days)
    except Exception as error:
        raise market_error_to_http_exception(error)
