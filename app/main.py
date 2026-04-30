from fastapi import FastAPI, HTTPException, Query

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


@app.get("/v1/market/technicals/{ticker}", response_model=TechnicalResponse)
async def get_market_technicals(
    ticker: str,
    days: int = Query(default=450, ge=80, le=1000),
):
    try:
        bars = await get_daily_bars(ticker=ticker, days=days)
        df = bars_to_dataframe(bars)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No market data found for {ticker}")

        summary = build_technical_summary(df)

        return {
            "ticker": ticker.upper(),
            **summary,
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))