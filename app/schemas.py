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
    above_20dma: bool = Field(description="Whether latest close is above the 20-day SMA.")
    above_50dma: bool = Field(description="Whether latest close is above the 50-day SMA.")
    above_200dma: bool = Field(description="Whether latest close is above the 200-day SMA.")
    ma_alignment: Literal["bullish", "bearish", "mixed", "unknown"] = Field(
        description="Moving-average alignment label based on price and 20/50/200-day SMAs."
    )
    ema_crossover: Literal["bullish", "bearish", "none", "insufficient_data"] = Field(
        description="Fresh latest-bar EMA 12/26 crossover signal, if any."
    )
    trend_score: int = Field(
        description="Number of positive trend components based on available moving-average conditions."
    )
    trend_score_max: int = Field(
        description="Maximum number of trend components that could be evaluated with available data."
    )
    trend_strength: Literal[
        "strong_uptrend",
        "constructive",
        "mixed_or_weak",
        "bearish_or_broken",
        "partial_constructive",
        "partial_bearish_or_broken",
        "unknown_or_partial",
    ] = Field(description="Compact trend-strength label derived from trend_score and trend_score_max.")
    trend_score_components: "TrendScoreComponents" = Field(
        description="Individual trend-score conditions. Null means the component lacked enough data."
    )


class TrendScoreComponents(BaseModel):
    price_above_sma_20: bool | None = Field(
        description="Whether latest close is above the 20-day SMA."
    )
    price_above_sma_50: bool | None = Field(
        description="Whether latest close is above the 50-day SMA."
    )
    price_above_sma_200: bool | None = Field(
        description="Whether latest close is above the 200-day SMA."
    )
    sma_20_above_sma_50: bool | None = Field(
        description="Whether the 20-day SMA is above the 50-day SMA."
    )
    sma_50_above_sma_200: bool | None = Field(
        description="Whether the 50-day SMA is above the 200-day SMA."
    )


class MovingAverages(BaseModel):
    sma_20: float | None = Field(description="20-day simple moving average.")
    sma_50: float | None = Field(description="50-day simple moving average.")
    sma_200: float | None = Field(description="200-day simple moving average.")
    ema_12: float | None = Field(description="12-day exponential moving average.")
    ema_26: float | None = Field(description="26-day exponential moving average.")
    distance_from_sma_20_pct: float | None = Field(
        description="Percent distance from latest close to 20-day SMA."
    )
    distance_from_sma_50_pct: float | None = Field(
        description="Percent distance from latest close to 50-day SMA."
    )
    distance_from_sma_200_pct: float | None = Field(
        description="Percent distance from latest close to 200-day SMA."
    )


class VolumeSummary(BaseModel):
    latest_volume: float | None = Field(description="Latest daily volume.")
    avg_20d_volume: float | None = Field(
        description="20-day average volume including the latest candle."
    )
    previous_20d_avg_volume: float | None = Field(
        description="20-day average volume before the latest candle; preferred for setup confirmation."
    )
    volume_ratio_vs_20d: float | None = Field(
        description="Latest volume divided by 20-day average volume including the latest candle."
    )
    volume_ratio_vs_previous_20d: float | None = Field(
        description="Latest volume divided by the previous 20-day average volume."
    )
    volume_signal: Literal["very_high", "above_average", "normal", "below_average", "unknown"] = Field(
        description="Volume label based on volume_ratio_vs_previous_20d."
    )
    price_volume_confirmation: Literal[
        "up_on_above_average_volume",
        "up_on_low_volume",
        "down_on_above_average_volume",
        "down_on_low_volume",
        "flat_or_mixed",
        "unknown",
    ] = Field(description="Price direction versus previous close combined with volume_signal.")


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


class Breakout(BaseModel):
    previous_20d_high: float | None = Field(
        description="Highest high from the 20 bars before the latest candle."
    )
    previous_20d_low: float | None = Field(
        description="Lowest low from the 20 bars before the latest candle."
    )
    previous_60d_high: float | None = Field(
        description="Highest high from the 60 bars before the latest candle."
    )
    previous_60d_low: float | None = Field(
        description="Lowest low from the 60 bars before the latest candle."
    )
    high_above_previous_20d_high: bool | None = Field(
        description="Whether latest intraday high exceeded the previous 20-day high."
    )
    close_above_previous_20d_high: bool | None = Field(
        description="Whether latest close exceeded the previous 20-day high."
    )
    low_below_previous_20d_low: bool | None = Field(
        description="Whether latest intraday low broke below the previous 20-day low."
    )
    close_below_previous_20d_low: bool | None = Field(
        description="Whether latest close broke below the previous 20-day low."
    )
    high_above_previous_60d_high: bool | None = Field(
        description="Whether latest intraday high exceeded the previous 60-day high."
    )
    close_above_previous_60d_high: bool | None = Field(
        description="Whether latest close exceeded the previous 60-day high."
    )
    low_below_previous_60d_low: bool | None = Field(
        description="Whether latest intraday low broke below the previous 60-day low."
    )
    close_below_previous_60d_low: bool | None = Field(
        description="Whether latest close broke below the previous 60-day low."
    )
    breakout_volume_confirmed: bool = Field(
        description="Whether a closing breakout also had latest volume at least 1.3x previous 20-day average volume."
    )
    breakdown_volume_confirmed: bool = Field(
        description="Whether a closing breakdown also had latest volume at least 1.3x previous 20-day average volume."
    )


class Structure(BaseModel):
    close_vs_previous_20d_high_pct: float | None = Field(
        description="Percent distance from latest close to previous 20-day high."
    )
    close_vs_previous_20d_low_pct: float | None = Field(
        description="Percent distance from latest close to previous 20-day low."
    )
    close_vs_previous_60d_high_pct: float | None = Field(
        description="Percent distance from latest close to previous 60-day high."
    )
    close_vs_previous_60d_low_pct: float | None = Field(
        description="Percent distance from latest close to previous 60-day low."
    )
    near_previous_20d_high: bool | None = Field(
        description="Whether latest close is within 3 percent of the previous 20-day high."
    )
    near_previous_20d_low: bool | None = Field(
        description="Whether latest close is within 3 percent of the previous 20-day low."
    )
    range_position_20d_pct: float | None = Field(
        description="Latest close position inside the previous 20-day range; 0 is low and 100 is high."
    )
    range_position_60d_pct: float | None = Field(
        description="Latest close position inside the previous 60-day range; 0 is low and 100 is high."
    )


class Liquidity(BaseModel):
    avg_20d_dollar_volume: float | None = Field(
        description="20-day average volume multiplied by latest close."
    )
    liquidity_tier: Literal["high", "medium", "low", "unknown"] = Field(
        description="Rough liquidity tier based on avg_20d_dollar_volume."
    )


class Gap(BaseModel):
    gap_pct: float | None = Field(
        description="Percent gap from previous close to latest open."
    )
    gap_direction: Literal["up", "down", "none", "unknown"] = Field(
        description="Direction of latest open versus previous close."
    )
    large_gap: bool | None = Field(
        description="Whether absolute gap_pct is at least 2 percent."
    )


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
    breakout: Breakout
    structure: Structure
    liquidity: Liquidity
    gap: Gap
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
