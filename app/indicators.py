from typing import Literal

import numpy as np
import pandas as pd


def bars_to_dataframe(bars: list[dict]) -> pd.DataFrame:
    if not bars:
        return pd.DataFrame()

    df = pd.DataFrame(bars)

    df = df.rename(
        columns={
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
            "t": "timestamp",
        }
    )

    df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "open", "high", "low", "close", "volume"]]


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()

    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal

    return macd, signal, histogram


def calculate_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    standard_deviations: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    middle = close.rolling(period).mean()
    rolling_std = close.rolling(period).std()
    upper = middle + (rolling_std * standard_deviations)
    lower = middle - (rolling_std * standard_deviations)
    bandwidth_pct = ((upper - lower) / middle) * 100
    percent_b = (close - lower) / (upper - lower)

    return middle, upper, lower, bandwidth_pct, percent_b


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.rolling(period).mean()


def calculate_ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def detect_latest_ema_crossover(
    close: pd.Series,
    short_period: int = 12,
    long_period: int = 26,
) -> Literal["bullish", "bearish", "none", "insufficient_data"]:
    if len(close) < 2:
        return "insufficient_data"

    short_ema = calculate_ema(close, short_period)
    long_ema = calculate_ema(close, long_period)

    previous_diff = short_ema.iloc[-2] - long_ema.iloc[-2]
    latest_diff = short_ema.iloc[-1] - long_ema.iloc[-1]

    if pd.isna(previous_diff) or pd.isna(latest_diff):
        return "insufficient_data"

    if previous_diff <= 0 < latest_diff:
        return "bullish"
    if previous_diff >= 0 > latest_diff:
        return "bearish"

    return "none"


def pct_change_from_n_days_ago(close: pd.Series, n: int) -> float | None:
    if len(close) <= n:
        return None

    old = close.iloc[-n - 1]
    current = close.iloc[-1]

    if old == 0:
        return None

    return round((current / old - 1) * 100, 2)


def round_or_none(value, digits: int = 2):
    if value is None:
        return None

    if pd.isna(value) or np.isinf(value):
        return None

    return round(float(value), digits)


def pct_distance(value: float | None, reference: float | None) -> float | None:
    if value is None or reference is None or reference == 0:
        return None

    return round_or_none((value / reference - 1) * 100)


def range_position_pct(value: float, low: float | None, high: float | None) -> float | None:
    if low is None or high is None or high == low:
        return None

    return round_or_none(((value - low) / (high - low)) * 100)


def build_trend_score_components(
    price: float,
    sma_20: float | None,
    sma_50: float | None,
    sma_200: float | None,
) -> dict[str, bool | None]:
    return {
        "price_above_sma_20": None if sma_20 is None else price > sma_20,
        "price_above_sma_50": None if sma_50 is None else price > sma_50,
        "price_above_sma_200": None if sma_200 is None else price > sma_200,
        "sma_20_above_sma_50": None if sma_20 is None or sma_50 is None else sma_20 > sma_50,
        "sma_50_above_sma_200": None if sma_50 is None or sma_200 is None else sma_50 > sma_200,
    }


def classify_trend_strength(
    trend_score: int,
    trend_score_max: int,
) -> Literal[
    "strong_uptrend",
    "constructive",
    "mixed_or_weak",
    "bearish_or_broken",
    "partial_constructive",
    "partial_bearish_or_broken",
    "unknown_or_partial",
]:
    if trend_score_max < 5:
        if trend_score_max == 0:
            return "unknown_or_partial"
        if trend_score == trend_score_max:
            return "partial_constructive"
        if trend_score == 0:
            return "partial_bearish_or_broken"
        return "unknown_or_partial"

    if trend_score == 5:
        return "strong_uptrend"
    if trend_score >= 3:
        return "constructive"
    if trend_score >= 1:
        return "mixed_or_weak"
    return "bearish_or_broken"


def classify_volume_signal(
    volume_ratio: float | None,
) -> Literal["very_high", "above_average", "normal", "below_average", "unknown"]:
    if volume_ratio is None:
        return "unknown"
    if volume_ratio >= 2.0:
        return "very_high"
    if volume_ratio > 1.2:
        return "above_average"
    if volume_ratio < 0.8:
        return "below_average"
    return "normal"


def classify_price_volume_confirmation(
    latest_close: float,
    previous_close: float | None,
    volume_signal: str,
) -> Literal[
    "up_on_above_average_volume",
    "up_on_low_volume",
    "down_on_above_average_volume",
    "down_on_low_volume",
    "flat_or_mixed",
    "unknown",
]:
    if previous_close is None or volume_signal == "unknown":
        return "unknown"

    if latest_close > previous_close:
        if volume_signal in {"above_average", "very_high"}:
            return "up_on_above_average_volume"
        if volume_signal == "below_average":
            return "up_on_low_volume"
        return "flat_or_mixed"

    if latest_close < previous_close:
        if volume_signal in {"above_average", "very_high"}:
            return "down_on_above_average_volume"
        if volume_signal == "below_average":
            return "down_on_low_volume"
        return "flat_or_mixed"

    return "flat_or_mixed"


def classify_liquidity_tier(
    avg_20d_dollar_volume: float | None,
) -> Literal["high", "medium", "low", "unknown"]:
    if avg_20d_dollar_volume is None:
        return "unknown"
    if avg_20d_dollar_volume >= 500_000_000:
        return "high"
    if avg_20d_dollar_volume >= 50_000_000:
        return "medium"
    return "low"


def classify_gap_direction(gap_pct: float | None) -> Literal["up", "down", "none", "unknown"]:
    if gap_pct is None:
        return "unknown"
    if gap_pct > 0:
        return "up"
    if gap_pct < 0:
        return "down"
    return "none"


def build_technical_summary(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 50:
        raise ValueError("Not enough market data to compute technicals")

    data_warnings: list[str] = []
    bars_returned = len(df)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()
    df["ema_12"] = calculate_ema(close, 12)
    df["ema_26"] = calculate_ema(close, 26)

    (
        df["bollinger_middle"],
        df["bollinger_upper"],
        df["bollinger_lower"],
        df["bollinger_bandwidth_pct"],
        df["bollinger_percent_b"],
    ) = calculate_bollinger_bands(close, 20, 2.0)

    df["atr_14"] = calculate_atr(high, low, close, 14)

    df["rsi_14"] = calculate_rsi(close, 14)

    macd, macd_signal, macd_hist = calculate_macd(close)
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_histogram"] = macd_hist

    latest = df.iloc[-1]

    price = float(latest["close"])
    latest_open = float(latest["open"])
    latest_high = float(latest["high"])
    latest_low = float(latest["low"])
    previous_close = float(close.iloc[-2]) if len(close) >= 2 else None
    sma_20 = round_or_none(latest["sma_20"])
    sma_50 = round_or_none(latest["sma_50"])
    sma_200 = round_or_none(latest["sma_200"])
    ema_12 = round_or_none(latest["ema_12"])
    ema_26 = round_or_none(latest["ema_26"])

    avg_20d_volume = volume.rolling(20).mean().iloc[-1]
    previous_20d_avg_volume = volume.shift(1).rolling(20).mean().iloc[-1]
    latest_volume = float(latest["volume"])
    volume_ratio = latest_volume / avg_20d_volume if avg_20d_volume else None
    volume_ratio_vs_previous_20d = (
        latest_volume / previous_20d_avg_volume if previous_20d_avg_volume else None
    )
    volume_signal = classify_volume_signal(round_or_none(volume_ratio_vs_previous_20d))
    price_volume_confirmation = classify_price_volume_confirmation(
        latest_close=price,
        previous_close=previous_close,
        volume_signal=volume_signal,
    )

    recent_20 = df.tail(20)
    recent_60 = df.tail(60)
    recent_252 = df.tail(252)

    recent_support_20d = float(recent_20["low"].min())
    recent_resistance_20d = float(recent_20["high"].max())

    high_52w = None
    low_52w = None
    if bars_returned >= 252:
        high_52w = float(recent_252["high"].max())
        low_52w = float(recent_252["low"].min())
    else:
        data_warnings.append(
            "Fewer than 252 trading bars returned; 52-week high/low metrics are unavailable."
        )

    if bars_returned < 200:
        data_warnings.append(
            "Fewer than 200 trading bars returned; SMA 200 and related trend fields are unavailable."
        )

    if bars_returned < 61:
        data_warnings.append(
            "Fewer than 61 trading bars returned; 60-day breakout and structure fields are unavailable."
        )

    ma_alignment = "unknown"
    if sma_20 and sma_50 and sma_200:
        if price > sma_20 > sma_50 > sma_200:
            ma_alignment = "bullish"
        elif price < sma_20 < sma_50 < sma_200:
            ma_alignment = "bearish"
        else:
            ma_alignment = "mixed"

    macd_signal_text = "neutral"
    if latest["macd"] > latest["macd_signal"] and latest["macd_histogram"] > 0:
        macd_signal_text = "positive"
    elif latest["macd"] < latest["macd_signal"] and latest["macd_histogram"] < 0:
        macd_signal_text = "negative"

    ema_crossover = detect_latest_ema_crossover(close, 12, 26)

    trend_score_components = build_trend_score_components(price, sma_20, sma_50, sma_200)
    evaluable_trend_components = [
        component for component in trend_score_components.values() if component is not None
    ]
    trend_score = sum(1 for component in evaluable_trend_components if component)
    trend_score_max = len(evaluable_trend_components)
    trend_strength = classify_trend_strength(trend_score, trend_score_max)

    previous_20d_high = round_or_none(high.shift(1).rolling(20).max().iloc[-1])
    previous_20d_low = round_or_none(low.shift(1).rolling(20).min().iloc[-1])
    previous_60d_high = round_or_none(high.shift(1).rolling(60).max().iloc[-1])
    previous_60d_low = round_or_none(low.shift(1).rolling(60).min().iloc[-1])

    close_above_previous_20d_high = (
        None if previous_20d_high is None else price > previous_20d_high
    )
    close_above_previous_60d_high = (
        None if previous_60d_high is None else price > previous_60d_high
    )
    close_below_previous_20d_low = (
        None if previous_20d_low is None else price < previous_20d_low
    )
    close_below_previous_60d_low = (
        None if previous_60d_low is None else price < previous_60d_low
    )
    volume_confirmed = (
        volume_ratio_vs_previous_20d is not None and volume_ratio_vs_previous_20d >= 1.3
    )

    avg_20d_dollar_volume = (
        float(avg_20d_volume) * price if not pd.isna(avg_20d_volume) and avg_20d_volume else None
    )
    gap_pct = pct_distance(latest_open, previous_close)

    summary = {
        "as_of": str(latest["date"]),
        "bars_returned": bars_returned,
        "data_warnings": data_warnings,
        "price": round_or_none(price),
        "trend": {
            "above_20dma": bool(sma_20 and price > sma_20),
            "above_50dma": bool(sma_50 and price > sma_50),
            "above_200dma": bool(sma_200 and price > sma_200),
            "ma_alignment": ma_alignment,
            "ema_crossover": ema_crossover,
            "trend_score": trend_score,
            "trend_score_max": trend_score_max,
            "trend_strength": trend_strength,
            "trend_score_components": trend_score_components,
        },
        "moving_averages": {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "ema_12": ema_12,
            "ema_26": ema_26,
            "distance_from_sma_20_pct": pct_distance(price, sma_20),
            "distance_from_sma_50_pct": pct_distance(price, sma_50),
            "distance_from_sma_200_pct": pct_distance(price, sma_200),
        },
        "volume": {
            "latest_volume": round_or_none(latest_volume, 0),
            "avg_20d_volume": round_or_none(avg_20d_volume, 0),
            "previous_20d_avg_volume": round_or_none(previous_20d_avg_volume, 0),
            "volume_ratio_vs_20d": round_or_none(volume_ratio),
            "volume_ratio_vs_previous_20d": round_or_none(volume_ratio_vs_previous_20d),
            "volume_signal": volume_signal,
            "price_volume_confirmation": price_volume_confirmation,
        },
        "momentum": {
            "rsi_14": round_or_none(latest["rsi_14"]),
            "macd": round_or_none(latest["macd"]),
            "macd_signal": round_or_none(latest["macd_signal"]),
            "macd_histogram": round_or_none(latest["macd_histogram"]),
            "macd_signal_text": macd_signal_text,
            "return_5d_pct": pct_change_from_n_days_ago(close, 5),
            "return_20d_pct": pct_change_from_n_days_ago(close, 20),
            "return_60d_pct": pct_change_from_n_days_ago(close, 60),
        },
        "volatility": {
            "atr_14": round_or_none(latest["atr_14"]),
            "bollinger_middle": round_or_none(latest["bollinger_middle"]),
            "bollinger_upper": round_or_none(latest["bollinger_upper"]),
            "bollinger_lower": round_or_none(latest["bollinger_lower"]),
            "bollinger_bandwidth_pct": round_or_none(latest["bollinger_bandwidth_pct"]),
            "bollinger_percent_b": round_or_none(latest["bollinger_percent_b"]),
        },
        "levels": {
            "support_20d_low": round_or_none(recent_support_20d),
            "resistance_20d_high": round_or_none(recent_resistance_20d),
            "high_52w": round_or_none(high_52w),
            "low_52w": round_or_none(low_52w),
            "distance_from_52w_high_pct": round_or_none(
                (price / high_52w - 1) * 100 if high_52w else None
            ),
            "distance_from_52w_low_pct": round_or_none(
                (price / low_52w - 1) * 100 if low_52w else None
            ),
        },
        "breakout": {
            "previous_20d_high": previous_20d_high,
            "previous_20d_low": previous_20d_low,
            "previous_60d_high": previous_60d_high,
            "previous_60d_low": previous_60d_low,
            "high_above_previous_20d_high": (
                None if previous_20d_high is None else latest_high > previous_20d_high
            ),
            "close_above_previous_20d_high": close_above_previous_20d_high,
            "low_below_previous_20d_low": (
                None if previous_20d_low is None else latest_low < previous_20d_low
            ),
            "close_below_previous_20d_low": close_below_previous_20d_low,
            "high_above_previous_60d_high": (
                None if previous_60d_high is None else latest_high > previous_60d_high
            ),
            "close_above_previous_60d_high": close_above_previous_60d_high,
            "low_below_previous_60d_low": (
                None if previous_60d_low is None else latest_low < previous_60d_low
            ),
            "close_below_previous_60d_low": close_below_previous_60d_low,
            "breakout_volume_confirmed": bool(
                volume_confirmed
                and (close_above_previous_20d_high or close_above_previous_60d_high)
            ),
            "breakdown_volume_confirmed": bool(
                volume_confirmed
                and (close_below_previous_20d_low or close_below_previous_60d_low)
            ),
        },
        "structure": {
            "close_vs_previous_20d_high_pct": pct_distance(price, previous_20d_high),
            "close_vs_previous_20d_low_pct": pct_distance(price, previous_20d_low),
            "close_vs_previous_60d_high_pct": pct_distance(price, previous_60d_high),
            "close_vs_previous_60d_low_pct": pct_distance(price, previous_60d_low),
            "near_previous_20d_high": (
                None
                if previous_20d_high is None
                else abs((price / previous_20d_high - 1) * 100) <= 3
            ),
            "near_previous_20d_low": (
                None if previous_20d_low is None else abs((price / previous_20d_low - 1) * 100) <= 3
            ),
            "range_position_20d_pct": range_position_pct(
                price,
                previous_20d_low,
                previous_20d_high,
            ),
            "range_position_60d_pct": range_position_pct(
                price,
                previous_60d_low,
                previous_60d_high,
            ),
        },
        "liquidity": {
            "avg_20d_dollar_volume": round_or_none(avg_20d_dollar_volume, 0),
            "liquidity_tier": classify_liquidity_tier(avg_20d_dollar_volume),
        },
        "gap": {
            "gap_pct": gap_pct,
            "gap_direction": classify_gap_direction(gap_pct),
            "large_gap": None if gap_pct is None else abs(gap_pct) >= 2.0,
        },
        "candles_tail": [
            {
                "date": str(row["date"]),
                "open": round_or_none(row["open"]),
                "high": round_or_none(row["high"]),
                "low": round_or_none(row["low"]),
                "close": round_or_none(row["close"]),
                "volume": round_or_none(row["volume"], 0),
            }
            for _, row in df.tail(10).iterrows()
        ],
    }

    summary["technical_summary"] = build_summary_text(summary)

    return summary


def build_summary_text(summary: dict) -> str:
    trend = summary["trend"]
    moving_averages = summary["moving_averages"]
    momentum = summary["momentum"]
    volatility = summary["volatility"]
    volume = summary["volume"]

    ma_position = []
    if trend["above_20dma"]:
        ma_position.append("above the 20-day moving average")
    if trend["above_50dma"]:
        ma_position.append("above the 50-day moving average")
    if trend["above_200dma"]:
        ma_position.append("above the 200-day moving average")

    if ma_position:
        ma_text = ", ".join(ma_position)
    elif moving_averages["sma_20"] or moving_averages["sma_50"] or moving_averages["sma_200"]:
        ma_text = "below one or more major moving averages"
    else:
        ma_text = "with limited moving-average history"

    rsi_text = "RSI unavailable"
    if momentum["rsi_14"] is not None:
        rsi_text = f"RSI is {momentum['rsi_14']}"

    macd_text = f"MACD momentum is {momentum['macd_signal_text']}"

    ema_text = "no fresh EMA crossover"
    if trend["ema_crossover"] in {"bullish", "bearish"}:
        ema_text = f"{trend['ema_crossover']} EMA crossover detected"

    atr_text = "ATR unavailable"
    if volatility["atr_14"] is not None:
        atr_text = f"ATR(14) is {volatility['atr_14']}"

    volume_ratio = volume["volume_ratio_vs_20d"]
    volume_text = "20-day volume comparison is unavailable"
    if volume_ratio is not None:
        volume_text = f"volume is {volume_ratio}x its 20-day average"

    return (
        f"Technical trend is {trend['ma_alignment']}, price is {ma_text}, "
        f"{rsi_text}, {macd_text}, {ema_text}, {atr_text}, and {volume_text}."
    )
