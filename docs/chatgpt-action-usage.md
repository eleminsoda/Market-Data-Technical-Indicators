# Market Technical API Action Usage Guide

This guide tells a Custom GPT how to use the Market Technical API Action for deterministic market technical data.

## Document Scope

This document is a backend Action usage guide. It explains how a Custom GPT should call the Market Technical API Action and interpret its returned fields.

This document should not define the Custom GPT's full investment workflow, user-specific decision framework, long/short strategy rules, portfolio rules, or final action categories. Those belong in the Custom GPT Instructions, not in this backend usage guide.

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

Backend authentication works by matching the incoming `X-API-Key` header against the backend's configured `API_KEY` value. `ACTION_API_KEY` is also accepted as a backward-compatible environment-variable alias. If neither `API_KEY` nor `ACTION_API_KEY` is configured, authentication is disabled; this is convenient for local development but should not be used for public deployments.

Request flow:

```text
Custom GPT Action
  -- X-API-Key: API_KEY -->
Market Technical API backend
  -- apiKey=POLYGON_API_KEY -->
Polygon/Massive
```

The Custom GPT should only know the Action API key used in `X-API-Key`. It should never know or ask for `POLYGON_API_KEY`.

## Required Data Disclosure

When using Action-derived technical data, the assistant must disclose:

- `as_of` date.
- Latest close / price.
- That the data is daily-bar technical data, not intraday data.
- Relevant `data_warnings`.
- Whether trend scores are partial because `trend_score_max < 5`.
- That the output is technical-analysis context only, not financial advice.

## Daily Data Limitation

The Action returns daily-bar-derived data. It should not be used to make claims about:

- Live intraday price action.
- Real-time order flow.
- Intraday support/resistance.
- Minute-level momentum.
- Live volume pace during the current trading session.

If the user asks about intraday movement, say the Action only provides daily-bar technical context and use web search or another real-time data source if available.

## No Data, No Technical Claim

If the Action does not return a field, or the field is `null`, the assistant must not infer or fabricate it.

Examples:

- If `sma_200` is unavailable, do not discuss the stock as above or below the 200-day SMA.
- If `previous_20d_avg_volume` is unavailable, do not claim a volume-confirmed breakout or breakdown.
- If 52-week levels are unavailable, do not discuss proximity to 52-week highs or lows.

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
- `trend`: moving-average trend state, trend score, and trend-strength label.
- `moving_averages`: SMA/EMA values and percent distance from latest close to each SMA.
- `volume`: latest volume, previous-20-day volume baseline, volume signal, and price-volume confirmation.
- `momentum`: RSI, MACD, and short-term returns.
- `volatility`: Bollinger Bands and ATR.
- `levels`: 20-day support/resistance and 52-week levels when available.
- `breakout`: prior 20/60-day high-low levels and close/intraday breakout or breakdown flags.
- `structure`: latest close position versus previous 20/60-day ranges.
- `liquidity`: 20-day dollar-volume context and liquidity tier.
- `gap`: latest open versus previous close gap context.
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
    "ema_crossover": "none",
    "trend_score": 5,
    "trend_score_max": 5,
    "trend_strength": "strong_uptrend",
    "trend_score_components": {
      "price_above_sma_20": true,
      "price_above_sma_50": true,
      "price_above_sma_200": true,
      "sma_20_above_sma_50": true,
      "sma_50_above_sma_200": true
    }
  },
  "moving_averages": {
    "sma_20": 264.36,
    "sma_50": 260.69,
    "sma_200": 254.52,
    "ema_12": 267.99,
    "ema_26": 264.28,
    "distance_from_sma_20_pct": 2.2,
    "distance_from_sma_50_pct": 3.64,
    "distance_from_sma_200_pct": 6.15
  },
  "volume": {
    "latest_volume": 52000000,
    "avg_20d_volume": 43000000,
    "previous_20d_avg_volume": 41000000,
    "volume_ratio_vs_20d": 1.21,
    "volume_ratio_vs_previous_20d": 1.27,
    "volume_signal": "above_average",
    "price_volume_confirmation": "up_on_above_average_volume"
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
  },
  "breakout": {
    "previous_20d_high": 272.0,
    "previous_20d_low": 240.5,
    "previous_60d_high": 285.0,
    "previous_60d_low": 220.0,
    "high_above_previous_20d_high": true,
    "close_above_previous_20d_high": false,
    "low_below_previous_20d_low": false,
    "close_below_previous_20d_low": false,
    "high_above_previous_60d_high": false,
    "close_above_previous_60d_high": false,
    "low_below_previous_60d_low": false,
    "close_below_previous_60d_low": false,
    "breakout_volume_confirmed": false,
    "breakdown_volume_confirmed": false
  },
  "structure": {
    "close_vs_previous_20d_high_pct": -0.67,
    "close_vs_previous_20d_low_pct": 12.35,
    "close_vs_previous_60d_high_pct": -5.2,
    "close_vs_previous_60d_low_pct": 22.8,
    "near_previous_20d_high": true,
    "near_previous_20d_low": false,
    "range_position_20d_pct": 94.19,
    "range_position_60d_pct": 78.4
  },
  "liquidity": {
    "avg_20d_dollar_volume": 11610000000,
    "liquidity_tier": "high"
  },
  "gap": {
    "gap_pct": 0.42,
    "gap_direction": "up",
    "large_gap": false
  }
}
```

## Structured Field Reference

Use these structured fields for detailed reasoning. Use `technical_summary` only as a quick overview.

### Trend

- `trend_score`: number of positive moving-average trend components.
- `trend_score_max`: number of trend components that could be evaluated with available data.
- `trend_strength`: compact trend label.
- `trend_score_components`: raw boolean/null components behind the score.

Possible `trend_strength` values:

- `strong_uptrend`: all five trend components are positive.
- `constructive`: three or four of five full-history components are positive.
- `mixed_or_weak`: one or two of five full-history components are positive.
- `bearish_or_broken`: no full-history components are positive.
- `partial_constructive`: all available partial-history components are positive.
- `partial_bearish_or_broken`: no available partial-history components are positive.
- `unknown_or_partial`: insufficient or mixed partial-history components.

When `trend_score_max` is less than `5`, explicitly say the score is partial because not all long-term moving-average components were available.

Partial trend labels should not be ranked directly against full-history labels without mentioning `trend_score_max`. For example, `partial_constructive` with `3/3` means all available components are positive, but it does not necessarily mean the setup is stronger than `constructive` with `4/5`.

### Moving-Average Distance

Use `distance_from_sma_20_pct`, `distance_from_sma_50_pct`, and `distance_from_sma_200_pct` to explain proximity or extension. For example, "above the 20-day SMA" and "18% above the 20-day SMA" are very different technical setups.

If a distance field is `null`, the moving average was unavailable.

### Volume Confirmation

Prefer `volume_ratio_vs_previous_20d` over `volume_ratio_vs_20d` when discussing breakout or breakdown quality because it excludes the latest candle from the baseline.

`avg_20d_volume` is mainly general context and includes the latest candle. `previous_20d_avg_volume` excludes the latest candle and should be used for setup confirmation.

Possible `volume_signal` values:

- `very_high`: latest volume is at least 2.0x previous 20-day average volume.
- `above_average`: latest volume is above 1.2x previous 20-day average volume.
- `normal`: latest volume is between 0.8x and 1.2x previous 20-day average volume.
- `below_average`: latest volume is below 0.8x previous 20-day average volume.
- `unknown`: insufficient volume baseline.

Possible `price_volume_confirmation` values:

- `up_on_above_average_volume`
- `up_on_low_volume`
- `down_on_above_average_volume`
- `down_on_low_volume`
- `flat_or_mixed`
- `unknown`

`price_volume_confirmation` compares the latest close with the previous close. It does not compare latest open-to-close intraday candle movement.

Treat these labels as context, not buy/sell/hold signals.

### Breakout And Breakdown

Breakout and breakdown reference levels use prior candles only. The latest candle is excluded from `previous_20d_high`, `previous_20d_low`, `previous_60d_high`, and `previous_60d_low`.

Use close-based fields as stronger evidence:

- `close_above_previous_20d_high`
- `close_above_previous_60d_high`
- `close_below_previous_20d_low`
- `close_below_previous_60d_low`

Use intraday fields as weaker context if the close did not confirm:

- `high_above_previous_20d_high`
- `high_above_previous_60d_high`
- `low_below_previous_20d_low`
- `low_below_previous_60d_low`

Use `breakout_volume_confirmed` and `breakdown_volume_confirmed` only as confirmation context. They require a close-based breakout or breakdown plus latest volume at least 1.3x the previous 20-day average volume.

### Structure

Use `range_position_20d_pct` and `range_position_60d_pct` to locate the latest close inside the previous range:

- `0`: at the previous range low.
- `50`: near the middle of the previous range.
- `100`: at the previous range high.
- Above `100`: closing breakout above the prior range.
- Below `0`: closing breakdown below the prior range.

Use `near_previous_20d_high` and `near_previous_20d_low` as quick proximity flags. They are based on a 3% threshold.

### Liquidity

Use `avg_20d_dollar_volume` and `liquidity_tier` to qualify signal reliability and execution context.

Possible `liquidity_tier` values:

- `high`: average 20-day dollar volume is at least 500M.
- `medium`: average 20-day dollar volume is at least 50M and below 500M.
- `low`: average 20-day dollar volume is below 50M.
- `unknown`: insufficient data.

Lower-liquidity names can have noisier technical signals and wider execution risk.

### Gap

Use `gap_pct`, `gap_direction`, and `large_gap` to discuss latest open-versus-previous-close context.

Gap fields identify price gaps only. Use web search to explain why a gap occurred, such as earnings, company news, analyst actions, or macro events.

Possible `gap_direction` values:

- `up`
- `down`
- `none`
- `unknown`

`large_gap` is true when absolute `gap_pct` is at least 2%.

## How To Interpret Key Fields

Use `as_of` in answers so the user knows the market data date. Daily bars may lag intraday market prices.

Use `data_warnings` to qualify answers. If warnings mention insufficient history, avoid strong conclusions about SMA 200 or 52-week levels.

Use `trend.ma_alignment` as a compact trend label:

- `bullish`: price and moving averages are aligned upward.
- `bearish`: price and moving averages are aligned downward.
- `mixed`: signals are not aligned.
- `unknown`: insufficient moving-average history.

Use `trend.above_20dma`, `above_50dma`, and `above_200dma` to explain where price sits relative to major trend references.

Use `trend.trend_score`, `trend.trend_score_max`, and `trend.trend_strength` for comparisons across tickers. If `trend_score_max` is below 5, explain that the score is partial because some moving-average components lacked enough history.

Use `moving_averages.distance_from_sma_*_pct` to discuss whether price is near a moving average or extended from it. A small positive distance can mean constructive proximity; a very large positive distance can mean extension risk.

Use `volume.volume_ratio_vs_previous_20d`, `volume.volume_signal`, and `volume.price_volume_confirmation` for setup quality. Prefer the previous-20-day baseline for breakout/breakdown confirmation because it excludes the latest candle.

Use `momentum.rsi_14` cautiously:

- Above 70 can suggest stretched or overbought conditions.
- Below 30 can suggest weak or oversold conditions.
- RSI alone is not a buy or sell signal.

Use `momentum.macd_signal_text` to describe MACD momentum as `positive`, `negative`, or `neutral`.

Use `trend.ema_crossover` only as a fresh crossover signal. If it is `none`, do not imply there was no broader EMA trend; it only means no latest-bar crossover was detected.

Use `volatility.atr_14` for recent average daily price movement. Use Bollinger fields to discuss position inside the band, volatility compression/expansion, and potential stretch.

Use `levels.support_20d_low`, `levels.resistance_20d_high`, `high_52w`, and `low_52w` as reference levels, not guaranteed support or resistance.

Use `breakout.close_above_previous_20d_high` and `breakout.close_above_previous_60d_high` for closing breakouts. Intraday high flags are weaker if the close did not also confirm. Treat `breakout_volume_confirmed` and `breakdown_volume_confirmed` as setup context, not a trade signal.

Use `structure.range_position_20d_pct` and `range_position_60d_pct` to explain whether the latest close is near the bottom, middle, or top of recent ranges. Values above 100 or below 0 can occur during breakouts or breakdowns.

Use `liquidity.liquidity_tier` to qualify thinly traded names. Lower-liquidity tickers may have less reliable technical signals and wider execution risk.

Use `gap.gap_pct`, `gap_direction`, and `large_gap` to explain latest open-versus-previous-close context.

Use `candles_tail` when the user asks for recent price action, recent candles, or exact recent OHLCV values.

## Field Priority

For detailed reasoning, prefer structured fields over `technical_summary`.

Use `technical_summary` only as a quick overview. When there is a mismatch between `technical_summary` and structured fields, rely on the structured fields and explain the specific fields used.

## Batch Comparison Rule

When comparing multiple tickers, do not rank them solely by `trend_score`.

Use a combined view:

- `trend_score / trend_score_max`.
- `trend_strength`.
- Distance from 20/50/200-day SMAs.
- Volume confirmation.
- Breakout/breakdown state.
- Range position.
- Liquidity tier.
- Data warnings.

If some tickers have partial trend scores and others have full trend scores, explicitly call this out before comparing them.

## Recommended Answer Pattern

When responding to the user after calling the Action:

1. State the ticker, `as_of` date, and latest close.
2. Summarize the trend using `ma_alignment`, `trend_score`, `trend_strength`, and distance from SMAs.
3. Summarize momentum using RSI, MACD, and recent returns.
4. Summarize volume confirmation, especially for breakouts or breakdowns.
5. Summarize volatility using ATR and Bollinger Bands.
6. Mention breakout/structure, key support/resistance, or 52-week levels when relevant.
7. Mention liquidity and gap context when they affect interpretation.
8. Mention any `data_warnings`.
9. Add that the output is technical-analysis context, not financial advice.
10. If the question asks for news, catalysts, valuation, or fundamentals, combine this Action with web search and clearly separate technical data from external context.

Example phrasing:

```text
As of 2026-04-29, AAPL closed at 270.17. The technical trend is bullish with a 5/5 trend score and strong_uptrend label. Price is above the 20-, 50-, and 200-day SMAs, and it is 2.2% above the 20-day SMA, so it is not extremely extended from that short-term reference. RSI is 60.63 and MACD momentum is positive. Volume confirmation is up_on_above_average_volume. ATR(14) is 5.57, so recent daily movement has been meaningful. The close is near the upper part of its prior 20-day range, but there is no confirmed closing breakout.

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
- If the user asks whether to buy, sell, or hold, provide balanced technical context, note that the backend only supplies technical data, and avoid turning backend fields into a standalone investment decision.

## Minimal Backend Tool Instructions

Use the following in Custom GPT instructions when you only need backend tool-usage rules:

```text
Use getStockTechnicals for one ticker and getBatchStockTechnicals for 2 to 10 tickers. The default days value is 450; only request 80 to 1000 days. Use batch requests for comparisons or watchlists.

Use this Action for daily technical indicators, recent daily candles, trend state, trend scores, moving-average distance, volume confirmation, breakout/breakdown state, range structure, liquidity, gap context, volatility, and support/resistance references.

Use web search for news, earnings, macro, fundamentals, and qualitative context. Clearly separate Action-derived technical data from web/news context.

Always mention as_of, latest close, relevant data_warnings, and that this is technical-analysis context only, not financial advice.

Do not claim this Action provides real-time intraday data. Do not fabricate missing fields. Do not expose or request backend secrets.

For detailed reasoning, prefer structured fields over technical_summary.

If batch results contain errors, explain which tickers succeeded and which failed. If the API returns market_data_auth_failed, say the backend market-data provider key or base URL needs to be checked; do not ask the user for POLYGON_API_KEY.
```
