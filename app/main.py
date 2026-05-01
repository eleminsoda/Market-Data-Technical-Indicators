from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.indicators import bars_to_dataframe, build_technical_summary
from app.polygon_client import get_daily_bars
from app.schemas import ErrorResponse, TechnicalBatchRequest, TechnicalBatchResponse, TechnicalResponse


HTTP_422_UNPROCESSABLE_ENTITY = 422

app = FastAPI(
    title="Market Technical API",
    version="0.1.0",
    description="Market technical analysis API for GPT-powered trading research.",
)


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Market data provider rejected the request."},
    403: {"model": ErrorResponse, "description": "API key is missing or invalid."},
    404: {"model": ErrorResponse, "description": "Requested market data was not found."},
    422: {"model": ErrorResponse, "description": "Request validation failed."},
    429: {"model": ErrorResponse, "description": "Market data provider rate limit exceeded."},
    500: {"model": ErrorResponse, "description": "Unexpected server error."},
    502: {"model": ErrorResponse, "description": "Market data provider returned an upstream error."},
    504: {"model": ErrorResponse, "description": "Market data provider request timed out."},
}


def build_error_payload(
    status_code: int,
    message: str,
    error: str | None = None,
    retryable: bool | None = None,
) -> dict[str, Any]:
    if retryable is None:
        retryable = status_code in {
            status.HTTP_429_TOO_MANY_REQUESTS,
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_504_GATEWAY_TIMEOUT,
        }

    error_name_by_status = {
        status.HTTP_400_BAD_REQUEST: "bad_request",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        HTTP_422_UNPROCESSABLE_ENTITY: "invalid_request",
        status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_error",
        status.HTTP_502_BAD_GATEWAY: "upstream_error",
        status.HTTP_504_GATEWAY_TIMEOUT: "upstream_timeout",
    }

    return ErrorResponse(
        error=error or error_name_by_status.get(status_code, "request_error"),
        message=message,
        status_code=status_code,
        retryable=retryable,
    ).model_dump()


def http_exception_to_error_payload(error: HTTPException) -> dict[str, Any]:
    if isinstance(error.detail, dict):
        return ErrorResponse(**error.detail).model_dump()

    return build_error_payload(
        status_code=error.status_code,
        message=str(error.detail),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_, error: HTTPException):
    return JSONResponse(
        status_code=error.status_code,
        content=http_exception_to_error_payload(error),
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_, error: RequestValidationError):
    errors = error.errors()
    first_error = errors[0] if errors else {}
    location = ".".join(str(part) for part in first_error.get("loc", []))
    validation_message = first_error.get("msg", "Request validation failed.")

    if location:
        message = f"Invalid request field '{location}': {validation_message}"
    else:
        message = f"Invalid request: {validation_message}"

    if len(errors) > 1:
        message = f"{message} ({len(errors)} validation errors total)"

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_payload(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            error="invalid_request",
            retryable=False,
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, error: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_payload(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unexpected server error while building market technicals.",
            error="internal_error",
            retryable=False,
        ),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


async def verify_action_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    required_api_key = settings.required_api_key
    if not required_api_key:
        return

    if x_api_key != required_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
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
                detail=build_error_payload(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    message=(
                        "Polygon.io rate limit exceeded while fetching market data. "
                        "Retry after the provider window resets."
                    ),
                    error="polygon_rate_limited",
                    retryable=True,
                ),
            )

        if upstream_status == status.HTTP_404_NOT_FOUND:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Market data provider could not find data for the requested ticker.",
            )

        if upstream_status in {
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        }:
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=build_error_payload(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    message=(
                        "Market data provider rejected the configured API key or permissions. "
                        "Check POLYGON_API_KEY and POLYGON_BASE_URL."
                    ),
                    error="market_data_auth_failed",
                    retryable=False,
                ),
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
        return HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))

    return HTTPException(status_code=500, detail=str(error))


@app.post(
    "/v1/market/technicals/batch",
    response_model=TechnicalBatchResponse,
    operation_id="getBatchStockTechnicals",
    summary="Get batch stock technicals",
    description=(
        "Returns RSI, MACD, Bollinger Bands, ATR, EMA crossover, moving averages, "
        "trend score, volume confirmation, breakout, structure, liquidity, gap, "
        "support/resistance, 52-week levels, recent candles, warnings, "
        "and summaries for stock tickers."
    ),
    responses=ERROR_RESPONSES,
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
                    **http_exception_to_error_payload(http_error),
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
        "Returns RSI, MACD, Bollinger Bands, ATR, EMA crossover, moving averages, "
        "trend score, volume confirmation, breakout, structure, liquidity, gap, "
        "support/resistance, 52-week levels, recent candles, warnings, "
        "and a summary for one stock ticker."
    ),
    responses=ERROR_RESPONSES,
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
