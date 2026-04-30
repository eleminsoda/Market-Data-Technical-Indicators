import asyncio
import os

os.environ.setdefault("POLYGON_API_KEY", "test-key")

import app.polygon_client as polygon_client


class FakePolygonResponse:
    status_code = 200
    headers = {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "adjusted": True,
            "request_id": "request-1",
            "status": "OK",
            "queryCount": 1,
            "resultsCount": 1,
            "results": [{"c": 100, "h": 101, "l": 99, "o": 100, "t": 1, "v": 1000}],
        }


def test_get_daily_bars_caches_identical_requests(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def get(self, url: str, params: dict):
            calls.append((url, params))
            return FakePolygonResponse()

    polygon_client.clear_cache()
    monkeypatch.setattr(polygon_client.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(polygon_client.settings, "polygon_api_key", "test-key")
    monkeypatch.setattr(polygon_client.settings, "market_cache_ttl_seconds", 300)

    first_bars, first_metadata = asyncio.run(polygon_client.get_daily_bars("AAPL", days=450))
    second_bars, second_metadata = asyncio.run(polygon_client.get_daily_bars("aapl", days=450))

    assert len(calls) == 1
    assert first_bars == second_bars
    assert first_metadata["cache_hit"] is False
    assert second_metadata["cache_hit"] is True
