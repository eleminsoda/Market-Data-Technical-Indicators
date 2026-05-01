# Market Technical API

FastAPI backend for Custom GPT stock-research Actions.

The API fetches split-adjusted daily OHLCV data from Massive/Polygon, computes technical indicators, and returns compact GPT-friendly JSON with source metadata, cache status, a deterministic summary, and data-quality warnings.

## Architecture

```text
Custom GPT
  -> built-in web search for news and qualitative context
  -> GPT Action call to this FastAPI backend for market technicals
  -> Massive/Polygon API for source OHLCV data
```

Keep the market-data API key on the backend. ChatGPT should call this service, not Massive/Polygon directly.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```bash
POLYGON_API_KEY=your_polygon_key
API_KEY=your_optional_action_key
POLYGON_BASE_URL=https://api.massive.com
MARKET_CACHE_TTL_SECONDS=300
```

`API_KEY` is optional for local development. If set, callers must send it as `X-API-Key`.
`ACTION_API_KEY` is also supported for backward compatibility.
`POLYGON_BASE_URL` defaults to Massive's API host. `https://api.polygon.io` remains configurable for backward compatibility.
`MARKET_CACHE_TTL_SECONDS` defaults to 300 seconds.

For public deployments, set `API_KEY` and configure GPT Action authentication to send it as the `X-API-Key` header. Keep `POLYGON_API_KEY` server-side only; callers should never receive the market-data provider key.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `GET /v1/market/technicals/{ticker}`
- `POST /v1/market/technicals/batch`
- `GET /openapi.json`

## Technical fields

Responses include:

- Trend: price position vs 20/50/200-day SMAs, moving-average alignment, latest EMA crossover.
- Trend score: available moving-average components, maximum evaluable components, and trend-strength label.
- Moving averages: SMA 20/50/200, EMA 12/26, and percent distance from latest close to each SMA.
- Momentum: RSI 14, MACD/signal/histogram, MACD signal text, 5/20/60-day returns.
- Volume confirmation: latest volume, 20-day average volume, previous-20-day volume baseline, volume signal, and price-volume confirmation.
- Volatility: Bollinger Bands, Bollinger bandwidth, Bollinger percent B, and ATR 14.
- Levels: 20-day support/resistance and 52-week high/low metrics when enough history is available.
- Breakout and structure: prior 20/60-day high-low ranges, close/intraday breakout or breakdown flags, and range-position percentages.
- Liquidity and gap: 20-day dollar-volume tier and latest open versus previous close gap context.
- Recent candles: last 10 daily OHLCV bars.
- Metadata: source, adjusted flag, lookback days, bars returned, cache hit, warnings, and non-advice flag.

## Example request

```bash
curl 'http://localhost:8000/v1/market/technicals/AAPL?days=450' \
  -H 'X-API-Key: your_optional_action_key'
```

## Example batch request

```bash
curl -X POST 'http://localhost:8000/v1/market/technicals/batch' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your_optional_action_key' \
  -d '{"tickers":["AAPL","MSFT","NVDA"],"days":450}'
```

## GPT Action setup

1. Deploy this API to an HTTPS URL.
2. In the GPT editor, create an Action and import `https://your-domain.example/openapi.json`.
3. If `API_KEY` or `ACTION_API_KEY` is enabled, configure Action authentication as an API key using custom header `X-API-Key`.
4. In the GPT instructions, tell the GPT to use web search for news/context and this Action for deterministic market technical data.

See [ChatGPT Action Usage Guide](docs/chatgpt-action-usage.md) for copy-paste GPT instructions, expected response fields, interpretation guidance, and error handling.

## Error responses

Errors return structured, GPT-friendly JSON:

```json
{
  "error": "polygon_rate_limited",
  "message": "Polygon.io rate limit exceeded while fetching market data. Retry after the provider window resets.",
  "status_code": 429,
  "retryable": true
}
```

The OpenAPI schema documents structured responses for `400`, `403`, `404`, `422`, `429`, `500`, `502`, and `504`. Polygon rate limits are detected and returned as `429`. Upstream market-data authentication or permission failures return `502` with `error: "market_data_auth_failed"` so key/base-URL issues are easier to debug.

## Caching

Identical market-data requests are cached in memory for 5 minutes by default. This reduces repeated Polygon.io calls during GPT Action retries or follow-up questions. The cache is process-local and resets when the server restarts.

## Tests

```bash
pytest
```

The test suite covers RSI, MACD, returns, rounding, Bollinger Bands, ATR, EMA crossover detection, dataframe conversion, summary generation, endpoint validation, auth failures, upstream error mapping, batch partial failures, cache hits, trend scoring, breakout/breakdown detection, volume confirmation, liquidity, and gap fields.

## Safety notes

- This API returns technical-analysis data only; it does not make investment decisions.
- Repeated identical market-data requests are cached in memory for 5 minutes by default.
- Rotate your Polygon key if it was ever committed to git.
- Do not commit `.env`, `.venv/`, or `__pycache__/`.
