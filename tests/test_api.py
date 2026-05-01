import os

import httpx
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("POLYGON_API_KEY", "test-key")

import app.main as main


def make_polygon_bars(rows: int = 260) -> list[dict]:
    start_timestamp_ms = 1_704_067_200_000
    day_ms = 86_400_000

    return [
        {
            "o": 100 + index - 0.5,
            "h": 100 + index + 1.0,
            "l": 100 + index - 1.0,
            "c": 100 + index,
            "v": 1_000_000 + index,
            "t": start_timestamp_ms + (index * day_ms),
        }
        for index in range(rows)
    ]


def make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://api.example.test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("Upstream error", request=request, response=response)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    main.app.dependency_overrides.clear()
    yield
    main.app.dependency_overrides.clear()


@pytest.fixture
def client_without_auth():
    async def skip_auth():
        return None

    main.app.dependency_overrides[main.verify_action_api_key] = skip_auth
    with TestClient(main.app) as client:
        yield client


def install_fake_bars(
    monkeypatch: pytest.MonkeyPatch,
    empty_tickers: set[str] | None = None,
    cache_hit: bool = False,
) -> None:
    empty_tickers = empty_tickers or set()

    async def fake_get_daily_bars(ticker: str, days: int, adjusted: bool = True):
        if ticker in empty_tickers:
            return [], {"adjusted": adjusted, "cache_hit": False}

        return make_polygon_bars(), {"adjusted": adjusted, "cache_hit": cache_hit}

    monkeypatch.setattr(main, "get_daily_bars", fake_get_daily_bars)


def test_health_endpoint_returns_ok():
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_structured_error_responses():
    schema = main.app.openapi()
    responses = schema["paths"]["/v1/market/technicals/{ticker}"]["get"]["responses"]

    for status_code in ["400", "403", "404", "422", "429", "500", "502", "504"]:
        assert (
            responses[status_code]["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/ErrorResponse"
        )


def test_openapi_includes_descriptions_for_new_action_fields():
    schema = main.app.openapi()

    assert schema["components"]["schemas"]["Breakout"]["properties"]["previous_20d_high"][
        "description"
    ]
    assert schema["components"]["schemas"]["Structure"]["properties"]["range_position_20d_pct"][
        "description"
    ]
    assert schema["components"]["schemas"]["Liquidity"]["properties"]["liquidity_tier"][
        "description"
    ]
    assert schema["components"]["schemas"]["Gap"]["properties"]["gap_pct"]["description"]


def test_get_market_technicals_returns_gpt_friendly_payload(client_without_auth, monkeypatch):
    install_fake_bars(monkeypatch, cache_hit=True)

    response = client_without_auth.get("/v1/market/technicals/aapl?days=450")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "AAPL"
    assert body["bars_returned"] == 260
    assert body["cache_hit"] is True
    assert body["not_financial_advice"] is True
    assert len(body["candles_tail"]) == 10
    assert body["volatility"]["atr_14"] is not None
    assert body["trend"]["trend_score"] == 5
    assert body["moving_averages"]["distance_from_sma_20_pct"] is not None
    assert body["volume"]["volume_signal"] in {"normal", "above_average", "very_high"}
    assert body["breakout"]["previous_20d_high"] is not None
    assert body["structure"]["range_position_20d_pct"] is not None
    assert body["liquidity"]["liquidity_tier"] in {"high", "medium", "low", "unknown"}
    assert body["gap"]["gap_direction"] in {"up", "down", "none", "unknown"}
    assert "Technical trend is" in body["technical_summary"]


def test_validation_errors_use_structured_error_response(client_without_auth):
    response = client_without_auth.get("/v1/market/technicals/AAPL?days=79")

    assert response.status_code == 422
    assert response.json() == {
        "error": "invalid_request",
        "message": "Invalid request field 'query.days': Input should be greater than or equal to 80",
        "status_code": 422,
        "retryable": False,
    }


def test_action_api_key_blocks_missing_header(monkeypatch):
    monkeypatch.setattr(main.settings, "action_api_key", "secret")

    with TestClient(main.app) as client:
        response = client.get("/v1/market/technicals/AAPL?days=450")

    assert response.status_code == 403
    assert response.json() == {
        "error": "forbidden",
        "message": "Invalid or missing API key",
        "status_code": 403,
        "retryable": False,
    }


def test_upstream_auth_failure_returns_debuggable_error(client_without_auth, monkeypatch):
    async def fake_get_daily_bars(ticker: str, days: int, adjusted: bool = True):
        raise make_http_status_error(401)

    monkeypatch.setattr(main, "get_daily_bars", fake_get_daily_bars)

    response = client_without_auth.get("/v1/market/technicals/AAPL?days=450")

    assert response.status_code == 502
    assert response.json() == {
        "error": "market_data_auth_failed",
        "message": (
            "Market data provider rejected the configured API key or permissions. "
            "Check POLYGON_API_KEY and POLYGON_BASE_URL."
        ),
        "status_code": 502,
        "retryable": False,
    }


def test_upstream_rate_limit_returns_retryable_error(client_without_auth, monkeypatch):
    async def fake_get_daily_bars(ticker: str, days: int, adjusted: bool = True):
        raise make_http_status_error(429)

    monkeypatch.setattr(main, "get_daily_bars", fake_get_daily_bars)

    response = client_without_auth.get("/v1/market/technicals/AAPL?days=450")

    assert response.status_code == 429
    body = response.json()
    assert body["error"] == "polygon_rate_limited"
    assert body["status_code"] == 429
    assert body["retryable"] is True


def test_batch_returns_partial_failures(client_without_auth, monkeypatch):
    install_fake_bars(monkeypatch, empty_tickers={"MISSING"})

    response = client_without_auth.post(
        "/v1/market/technicals/batch",
        json={"tickers": ["AAPL", "MISSING"], "days": 450},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_count"] == 2
    assert body["returned_count"] == 1
    assert [result["ticker"] for result in body["results"]] == ["AAPL"]
    assert "breakout" in body["results"][0]
    assert "structure" in body["results"][0]
    assert "liquidity" in body["results"][0]
    assert "gap" in body["results"][0]
    assert body["errors"] == [
        {
            "ticker": "MISSING",
            "status_code": 404,
            "error": "not_found",
            "message": "No market data found for MISSING",
            "retryable": False,
        }
    ]
