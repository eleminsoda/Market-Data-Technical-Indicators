# Market Technical API

Polygon raw market data → backend computes indicators → GPT-friendly JSON.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

## Endpoints

- `GET /health`
- `POST /technical`

## Example request

```bash
curl -X POST http://localhost:8000/technical \
  -H 'Content-Type: application/json' \
  -d '{
    "ticker":"AAPL",
    "from_date":"2025-01-01",
    "to_date":"2025-04-01",
    "timespan":"day",
    "polygon_api_key":"YOUR_KEY"
  }'
```
