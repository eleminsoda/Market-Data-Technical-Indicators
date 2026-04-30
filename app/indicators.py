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
    sma_20 = round_or_none(latest["sma_20"])
    sma_50 = round_or_none(latest["sma_50"])
    sma_200 = round_or_none(latest["sma_200"])
    ema_12 = round_or_none(latest["ema_12"])
    ema_26 = round_or_none(latest["ema_26"])

    avg_20d_volume = volume.rolling(20).mean().iloc[-1]
    latest_volume = float(latest["volume"])
    volume_ratio = latest_volume / avg_20d_volume if avg_20d_volume else None

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
        },
        "moving_averages": {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "ema_12": ema_12,
            "ema_26": ema_26,
        },
        "volume": {
            "latest_volume": round_or_none(latest_volume, 0),
            "avg_20d_volume": round_or_none(avg_20d_volume, 0),
            "volume_ratio_vs_20d": round_or_none(volume_ratio),
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
