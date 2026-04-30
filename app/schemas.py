from typing import Literal

from pydantic import BaseModel, Field


class Trend(BaseModel):
    above_20dma: bool
    above_50dma: bool
    above_200dma: bool
    ma_alignment: Literal["bullish", "bearish", "mixed", "unknown"]


class MovingAverages(BaseModel):
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None


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
    price: float | None
    trend: Trend
    moving_averages: MovingAverages
    volume: VolumeSummary
    momentum: Momentum
    levels: Levels
    candles_tail: list[Candle]
