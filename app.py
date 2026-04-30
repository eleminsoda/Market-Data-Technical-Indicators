from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Market Technical API",
    description="Polygon raw market data -> computed indicators -> GPT-friendly JSON",
    version="0.1.0",
)


class TechnicalRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. AAPL")
    multiplier: int = Field(1, ge=1)
    timespan: str = Field("day", description="minute/hour/day/week/month")
    from_date: str = Field(..., description="YYYY-MM-DD")
    to_date: str = Field(..., description="YYYY-MM-DD")
    adjusted: bool = True
    sort: str = Field("asc", pattern="^(asc|desc)$")
    limit: int = Field(5000, ge=1, le=50000)
    polygon_api_key: str = Field(..., description="Polygon API key")

    sma_window: int = Field(20, ge=2)
    ema_window: int = Field(20, ge=2)
    rsi_window: int = Field(14, ge=2)
    bb_window: int = Field(20, ge=2)
    bb_std: float = Field(2.0, gt=0)


def fetch_polygon_aggs(req: TechnicalRequest) -> pd.DataFrame:
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{req.ticker.upper()}/range/"
        f"{req.multiplier}/{req.timespan}/{req.from_date}/{req.to_date}"
    )
    params = {
        "adjusted": str(req.adjusted).lower(),
        "sort": req.sort,
        "limit": req.limit,
        "apiKey": req.polygon_api_key,
    }
    response = requests.get(url, params=params, timeout=20)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail={"polygon_error": response.text, "url": response.url},
        )

    payload = response.json()
    results = payload.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail="No candle data returned from Polygon")

    df = pd.DataFrame(results)
    rename_map = {
        "t": "timestamp_ms",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
        "vw": "vwap",
        "n": "trades",
    }
    df = df.rename(columns=rename_map)
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    return df


def compute_indicators(df: pd.DataFrame, req: TechnicalRequest) -> pd.DataFrame:
    close = df["close"]

    df["sma"] = close.rolling(window=req.sma_window).mean()
    df["ema"] = close.ewm(span=req.ema_window, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=req.rsi_window).mean()
    avg_loss = loss.rolling(window=req.rsi_window).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    df["rsi"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    bb_mid = close.rolling(window=req.bb_window).mean()
    bb_std = close.rolling(window=req.bb_window).std()
    df["bb_middle"] = bb_mid
    df["bb_upper"] = bb_mid + req.bb_std * bb_std
    df["bb_lower"] = bb_mid - req.bb_std * bb_std

    return df


def _nan_to_none(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    return float(value)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "market-technical-api"}


@app.post("/technical")
def technical(req: TechnicalRequest) -> Dict[str, Any]:
    try:
        datetime.strptime(req.from_date, "%Y-%m-%d")
        datetime.strptime(req.to_date, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Dates must be YYYY-MM-DD") from exc

    df = fetch_polygon_aggs(req)
    df = compute_indicators(df, req)

    latest = df.iloc[-1]

    candles: List[Dict[str, Any]] = []
    for _, row in df.tail(200).iterrows():
        candles.append(
            {
                "timestamp": row["timestamp"].isoformat(),
                "open": _nan_to_none(row.get("open")),
                "high": _nan_to_none(row.get("high")),
                "low": _nan_to_none(row.get("low")),
                "close": _nan_to_none(row.get("close")),
                "volume": _nan_to_none(row.get("volume")),
                "indicators": {
                    "sma": _nan_to_none(row.get("sma")),
                    "ema": _nan_to_none(row.get("ema")),
                    "rsi": _nan_to_none(row.get("rsi")),
                    "macd": _nan_to_none(row.get("macd")),
                    "macd_signal": _nan_to_none(row.get("macd_signal")),
                    "macd_histogram": _nan_to_none(row.get("macd_histogram")),
                    "bb_middle": _nan_to_none(row.get("bb_middle")),
                    "bb_upper": _nan_to_none(row.get("bb_upper")),
                    "bb_lower": _nan_to_none(row.get("bb_lower")),
                },
            }
        )

    signal = "neutral"
    if latest["close"] > latest["sma"] and latest["macd"] > latest["macd_signal"]:
        signal = "bullish"
    elif latest["close"] < latest["sma"] and latest["macd"] < latest["macd_signal"]:
        signal = "bearish"

    return {
        "meta": {
            "ticker": req.ticker.upper(),
            "timespan": req.timespan,
            "multiplier": req.multiplier,
            "from": req.from_date,
            "to": req.to_date,
            "rows": int(len(df)),
            "source": "Polygon.io aggregates",
        },
        "latest_snapshot": {
            "timestamp": latest["timestamp"].isoformat(),
            "close": _nan_to_none(latest["close"]),
            "sma": _nan_to_none(latest["sma"]),
            "ema": _nan_to_none(latest["ema"]),
            "rsi": _nan_to_none(latest["rsi"]),
            "macd": _nan_to_none(latest["macd"]),
            "macd_signal": _nan_to_none(latest["macd_signal"]),
            "macd_histogram": _nan_to_none(latest["macd_histogram"]),
            "bb_middle": _nan_to_none(latest["bb_middle"]),
            "bb_upper": _nan_to_none(latest["bb_upper"]),
            "bb_lower": _nan_to_none(latest["bb_lower"]),
            "signal": signal,
        },
        "candles": candles,
        "gpt_prompt_hint": (
            "You are a market analyst. Use latest_snapshot for directional bias, "
            "use RSI for momentum/overbought-oversold, MACD for trend confirmation, "
            "and Bollinger bands for volatility context."
        ),
    }
