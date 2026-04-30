# ChatGPT Action Usage Guide

This guide tells a Custom GPT how to use the Market Technical API Action for deterministic market technical data.

## Purpose

Use this Action to fetch recent daily OHLCV-derived technical indicators for stock tickers. The Action is designed to complement, not replace, web search:

- Use this Action for structured technical data, indicators, trend state, levels, recent candles, and deterministic summary text.
- Use web search or other trusted sources for news, events, fundamentals, earnings context, analyst commentary, macro context, and real-time qualitative updates.
- Do not call Polygon or Massive directly. The backend owns the market-data provider API key.
- Do not expose or ask for `POLYGON_API_KEY`.
- Treat all outputs as technical-analysis data, not investment advice.

## Available Operations

### `getStockTechnicals`

Use for one ticker.

Endpoint:

```text
GET /v1/market/technicals/{ticker}
```

Parameters:

- `ticker`: required stock ticker, for example `AAPL`.
- `days`: optional calendar-day lookback, default `450`, minimum `80`, maximum `1000`.

Use this operation when the user asks about a single stock or when the answer only needs one ticker.

### `getBatchStockTechnicals`

Use for multiple tickers.

Endpoint:

```text
POST /v1/market/technicals/batch
```

Request body:

```json
{
  "tickers": ["AAPL", "MSFT", "NVDA"],
  "days": 450
}
```

Parameters:

- `tickers`: required list of 1 to 10 ticker strings.
- `days`: optional calendar-day lookback, default `450`, minimum `80`, maximum `1000`.

Use this operation when comparing multiple tickers, screening a small watchlist, or answering a question that naturally needs more than one stock. Duplicate tickers may be returned only once in `results`; compare `requested_count` and `returned_count`.

## Authentication

If the deployed Action requires authentication, send the configured Action API key in this header:

```text
X-API-Key: <action-api-key>
```

This is the API key for the backend Action, not the market-data provider key.

## Expected Successful Response

Successful ticker responses include these top-level fields:

- `ticker`: normalized uppercase ticker.
- `as_of`: date of the latest daily bar used.
- `source`: market data source label, currently `polygon`.
- `adjusted`: whether bars are adjusted.
- `timespan`: currently `day`.
- `requested_lookback_days`: requested calendar-day lookback.
- `bars_returned`: number of daily bars returned by the provider.
- `cache_hit`: whether the backend served cached market data.
- `data_warnings`: warnings about insufficient history or data quality.
- `not_financial_advice`: always `true`.
- `technical_summary`: concise deterministic summary generated from the indicators.
- `price`: latest close.
- `trend`: moving-average trend state.
- `moving_averages`: SMA and EMA values.
- `volume`: latest and average volume context.
- `momentum`: RSI, MACD, and short-term returns.
- `volatility`: Bollinger Bands and ATR.
- `levels`: 20-day support/resistance and 52-week levels when available.
- `candles_tail`: last 10 daily OHLCV candles.

Example abbreviated response:

```json
{
  "ticker": "AAPL",
  "as_of": "2026-04-29",
  "source": "polygon",
  "adjusted": true,
  "timespan": "day",
  "requested_lookback_days": 450,
  "bars_returned": 310,
  "cache_hit": true,
  "data_warnings": [],
  "not_financial_advice": true,
  "technical_summary": "Technical trend is bullish...",
  "price": 270.17,
  "trend": {
    "above_20dma": true,
    "above_50dma": true,
    "above_200dma": true,
    "ma_alignment": "bullish",
    "ema_crossover": "none"
  },
  "moving_averages": {
    "sma_20": 264.36,
    "sma_50": 260.69,
    "sma_200": 254.52,
    "ema_12": 267.99,
    "ema_26": 264.28
  },
  "momentum": {
    "rsi_14": 60.63,
    "macd": 3.87,
    "macd_signal": 2.91,
    "macd_histogram": 0.96,
    "macd_signal_text": "positive",
    "return_5d_pct": 1.54,
    "return_20d_pct": 4.1,
    "return_60d_pct": 8.6
  },
  "volatility": {
    "atr_14": 5.57,
    "bollinger_middle": 264.36,
    "bollinger_upper": 277.51,
    "bollinger_lower": 251.22,
    "bollinger_bandwidth_pct": 9.94,
    "bollinger_percent_b": 0.72
  }
}
```

## How To Interpret Key Fields

Use `as_of` in answers so the user knows the market data date. Daily bars may lag intraday market prices.

Use `data_warnings` to qualify answers. If warnings mention insufficient history, avoid strong conclusions about SMA 200 or 52-week levels.

Use `trend.ma_alignment` as a compact trend label:

- `bullish`: price and moving averages are aligned upward.
- `bearish`: price and moving averages are aligned downward.
- `mixed`: signals are not aligned.
- `unknown`: insufficient moving-average history.

Use `trend.above_20dma`, `above_50dma`, and `above_200dma` to explain where price sits relative to major trend references.

Use `momentum.rsi_14` cautiously:

- Above 70 can suggest stretched or overbought conditions.
- Below 30 can suggest weak or oversold conditions.
- RSI alone is not a buy or sell signal.

Use `momentum.macd_signal_text` to describe MACD momentum as `positive`, `negative`, or `neutral`.

Use `trend.ema_crossover` only as a fresh crossover signal. If it is `none`, do not imply there was no broader EMA trend; it only means no latest-bar crossover was detected.

Use `volatility.atr_14` for recent average daily price movement. Use Bollinger fields to discuss position inside the band, volatility compression/expansion, and potential stretch.

Use `levels.support_20d_low`, `levels.resistance_20d_high`, `high_52w`, and `low_52w` as reference levels, not guaranteed support or resistance.

Use `candles_tail` when the user asks for recent price action, recent candles, or exact recent OHLCV values.

## Recommended Answer Pattern

When responding to the user after calling the Action:

1. State the ticker, `as_of` date, and latest close.
2. Summarize the trend using moving averages and `ma_alignment`.
3. Summarize momentum using RSI, MACD, and recent returns.
4. Summarize volatility using ATR and Bollinger Bands.
5. Mention key support/resistance or 52-week levels when relevant.
6. Mention any `data_warnings`.
7. Add that the output is technical-analysis context, not financial advice.
8. If the question asks for news, catalysts, valuation, or fundamentals, combine this Action with web search and clearly separate technical data from external context.

Example phrasing:

```text
As of 2026-04-29, AAPL closed at 270.17. The technical trend is bullish: price is above the 20-, 50-, and 200-day SMAs, and MACD momentum is positive. RSI is 60.63, which is constructive but not overbought. ATR(14) is 5.57, so recent daily movement has been meaningful. Key 20-day reference levels are ...

This is technical-analysis context only, not financial advice.
```

## Error Handling

Errors use this shape:

```json
{
  "error": "invalid_request",
  "message": "Invalid request field 'query.days': Input should be greater than or equal to 80",
  "status_code": 422,
  "retryable": false
}
```

Common statuses:

- `400`: provider rejected the request. Check ticker format or parameters.
- `403`: missing or invalid Action API key.
- `404`: no market data found for the requested ticker.
- `422`: invalid request, such as `days` outside the allowed range.
- `429`: provider rate limit. Retry later if `retryable` is true.
- `500`: unexpected backend error.
- `502`: upstream market-data provider error or backend provider-key problem.
- `504`: upstream market-data request timed out.

For batch responses, individual ticker failures appear in the `errors` array while valid tickers appear in `results`. Do not treat a `200` batch response as full success unless `errors` is empty.

If `error` is `market_data_auth_failed`, tell the user the backend provider key or base URL needs attention. Do not ask the user for the provider key in chat.

## Safety And Scope Rules

- Do not present technical indicators as a guarantee or recommendation.
- Do not say the Action provides real-time intraday prices; it returns daily bars.
- Do not ignore `as_of`, `bars_returned`, or `data_warnings`.
- Do not reveal, infer, or request backend secrets.
- Do not fabricate missing fields. If a field is `null`, say it is unavailable.
- Do not overstate signals when indicators are mixed.
- If the user asks whether to buy, sell, or hold, provide balanced technical context and suggest considering risk tolerance, time horizon, fundamentals, and professional advice.

## Copy-Paste GPT Instructions

Use the following in the Custom GPT instructions:

```text
You have access to the Market Technical API Action for deterministic daily stock technical data.

Use getStockTechnicals for one ticker and getBatchStockTechnicals for 2 to 10 tickers. The default days value is 450; only request 80 to 1000 days. Use batch requests for comparisons or watchlists.

Use this Action for technical indicators, recent daily candles, trend state, volatility, support/resistance references, and structured market-data summaries. Use web search for news, earnings, macro context, fundamentals, and qualitative context. Clearly separate Action-derived technical data from web/news context.

Always mention the response as_of date, latest close, relevant warnings, and that the analysis is not financial advice. Do not claim the data is intraday or real time. Treat support/resistance and indicators as reference points, not guarantees.

If a response has data_warnings, qualify the analysis. If batch results contain errors, explain which tickers succeeded and which failed. If the API returns market_data_auth_failed, say the backend market-data provider key or base URL needs to be checked; do not ask the user for POLYGON_API_KEY.

Never expose or request backend secrets. Never call Polygon or Massive directly.
```
