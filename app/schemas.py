from typing import Literal

from pydantic import BaseModel, Field


class TechnicalBatchRequest(BaseModel):
    tickers: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Stock tickers to analyze in one request.",
    )
    days: int = Field(
        default=450,
        ge=80,
        le=1000,
        description="Calendar-day lookback used to fetch daily bars.",
    )


class Trend(BaseModel):
    above_20dma: bool
    above_50dma: bool
    above_200dma: bool
    ma_alignment: Literal["bullish", "bearish", "mixed", "unknown"]
    ema_crossover: Literal["bullish", "bearish", "none", "insufficient_data"]


class MovingAverages(BaseModel):
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    ema_12: float | None
    ema_26: float | None


class VolumeSummary(BaseModel):
    latest_volume: float | None
    avg_20d_volume: float | None
    volume_ratio_vs_20d: float | None


class Momentum(BaseModel):
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    macd_signal_text: Literal["positive", "negative", "neutral"]
    return_5d_pct: float | None
    return_20d_pct: float | None
    return_60d_pct: float | None


class Volatility(BaseModel):
    atr_14: float | None
    bollinger_middle: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    bollinger_bandwidth_pct: float | None
    bollinger_percent_b: float | None


class Levels(BaseModel):
    support_20d_low: float | None
    resistance_20d_high: float | None
    high_52w: float | None
    low_52w: float | None
    distance_from_52w_high_pct: float | None
    distance_from_52w_low_pct: float | None


class Candle(BaseModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


class TechnicalResponse(BaseModel):
    ticker: str
    as_of: str
    source: Literal["polygon"] = "polygon"
    adjusted: bool
    timespan: Literal["day"] = "day"
    requested_lookback_days: int
    bars_returned: int
    cache_hit: bool
    data_warnings: list[str] = Field(default_factory=list)
    not_financial_advice: bool = True
    technical_summary: str
    price: float | None
    trend: Trend
    moving_averages: MovingAverages
    volume: VolumeSummary
    momentum: Momentum
    volatility: Volatility
    levels: Levels
    candles_tail: list[Candle]


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int
    retryable: bool = False


class TechnicalBatchError(BaseModel):
    ticker: str
    status_code: int
    error: str
    message: str
    retryable: bool = False


class TechnicalBatchResponse(BaseModel):
    requested_count: int
    returned_count: int
    results: list[TechnicalResponse]
    errors: list[TechnicalBatchError] = Field(default_factory=list)
