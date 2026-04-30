# Market Technical API

FastAPI backend for Custom GPT stock-research Actions.

The API fetches split-adjusted daily OHLCV data from Polygon, computes technical indicators, and returns compact GPT-friendly JSON with source metadata, cache status, and data-quality warnings.

## Architecture

```text
Custom GPT
  -> built-in web search for news and qualitative context
  -> GPT Action call to this FastAPI backend for market technicals
  -> Polygon.io API for source OHLCV data
```

Keep the Polygon key on the backend. ChatGPT should call this service, not Polygon directly.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```bash
POLYGON_API_KEY=your_polygon_key
ACTION_API_KEY=your_optional_action_key
```

`ACTION_API_KEY` is optional for local development. If set, callers must send it as `X-API-Key`.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `GET /v1/market/technicals/{ticker}`
- `GET /openapi.json`

## Example request

```bash
curl 'http://localhost:8000/v1/market/technicals/AAPL?days=450' \
  -H 'X-API-Key: your_optional_action_key'
```

## GPT Action setup

1. Deploy this API to an HTTPS URL.
2. In the GPT editor, create an Action and import `https://your-domain.example/openapi.json`.
3. If `ACTION_API_KEY` is enabled, configure Action authentication as an API key using custom header `X-API-Key`.
4. In the GPT instructions, tell the GPT to use web search for news/context and this Action for deterministic market technical data.

## Safety notes

- This API returns technical-analysis data only; it does not make investment decisions.
- Repeated identical Polygon requests are cached in memory for 5 minutes.
- Rotate your Polygon key if it was ever committed to git.
- Do not commit `.env`, `.venv/`, or `__pycache__/`.
