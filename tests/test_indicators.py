import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.indicators import (
    bars_to_dataframe,
    build_summary_text,
    build_technical_summary,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    detect_latest_ema_crossover,
    pct_change_from_n_days_ago,
    round_or_none,
)


def make_ohlcv_frame(rows: int = 260, start: float = 100.0, step: float = 1.0) -> pd.DataFrame:
    close = pd.Series([start + (index * step) for index in range(rows)], dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=rows).date,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": pd.Series([1_000_000 + index for index in range(rows)], dtype=float),
        }
    )


def test_bars_to_dataframe_returns_empty_dataframe_for_empty_bars():
    assert bars_to_dataframe([]).empty


def test_bars_to_dataframe_renames_sorts_and_selects_expected_columns():
    bars = [
        {"o": 2, "h": 3, "l": 1, "c": 2.5, "v": 200, "t": 1_704_153_600_000},
        {"o": 1, "h": 2, "l": 0, "c": 1.5, "v": 100, "t": 1_704_067_200_000},
    ]

    df = bars_to_dataframe(bars)

    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert df["date"].tolist() == [date(2024, 1, 1), date(2024, 1, 2)]
    assert df["close"].tolist() == [1.5, 2.5]


def test_calculate_rsi_preserves_input_length():
    close = pd.Series(range(1, 21), dtype=float)

    assert len(calculate_rsi(close)) == len(close)


def test_calculate_rsi_has_nan_before_period_is_available():
    close = pd.Series(range(1, 21), dtype=float)

    assert math.isnan(calculate_rsi(close, 14).iloc[13])


def test_calculate_rsi_is_100_for_uninterrupted_gains_after_period():
    close = pd.Series(range(1, 21), dtype=float)

    assert calculate_rsi(close, 14).iloc[-1] == 100


def test_calculate_rsi_matches_manual_mixed_gain_loss_example():
    close = pd.Series([10, 12, 11, 13, 12], dtype=float)

    assert round(calculate_rsi(close, 4).iloc[-1], 2) == 66.67


def test_calculate_macd_returns_zero_lines_for_constant_prices():
    close = pd.Series([10.0] * 40)
    macd, signal, histogram = calculate_macd(close)

    assert macd.iloc[-1] == 0
    assert signal.iloc[-1] == 0
    assert histogram.iloc[-1] == 0


def test_calculate_macd_histogram_equals_macd_minus_signal():
    close = pd.Series(range(1, 50), dtype=float)
    macd, signal, histogram = calculate_macd(close)

    assert histogram.iloc[-1] == pytest.approx(macd.iloc[-1] - signal.iloc[-1])


def test_calculate_macd_is_positive_for_sustained_uptrend():
    close = pd.Series(range(1, 60), dtype=float)
    macd, _, _ = calculate_macd(close)

    assert macd.iloc[-1] > 0


def test_pct_change_from_n_days_ago_returns_none_for_short_series():
    assert pct_change_from_n_days_ago(pd.Series([10, 11], dtype=float), 2) is None


def test_pct_change_from_n_days_ago_returns_none_when_old_price_is_zero():
    assert pct_change_from_n_days_ago(pd.Series([0, 1, 2], dtype=float), 2) is None


def test_pct_change_from_n_days_ago_returns_rounded_percentage():
    assert pct_change_from_n_days_ago(pd.Series([100, 105, 110], dtype=float), 2) == 10.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (np.nan, None),
        (np.inf, None),
        (1.234, 1.23),
    ],
)
def test_round_or_none_handles_numeric_edge_cases(value, expected):
    assert round_or_none(value) == expected


def test_calculate_bollinger_bands_has_nan_before_period_is_available():
    close = pd.Series(range(1, 21), dtype=float)
    middle, *_ = calculate_bollinger_bands(close, period=20)

    assert math.isnan(middle.iloc[18])


def test_calculate_bollinger_bands_middle_is_rolling_mean():
    close = pd.Series(range(1, 21), dtype=float)
    middle, *_ = calculate_bollinger_bands(close, period=20)

    assert middle.iloc[-1] == 10.5


def test_calculate_bollinger_bands_upper_and_lower_use_two_standard_deviations():
    close = pd.Series(range(1, 21), dtype=float)
    middle, upper, lower, _, _ = calculate_bollinger_bands(close, period=20)
    expected_std = close.rolling(20).std().iloc[-1]

    assert upper.iloc[-1] == pytest.approx(middle.iloc[-1] + (2 * expected_std))
    assert lower.iloc[-1] == pytest.approx(middle.iloc[-1] - (2 * expected_std))


def test_calculate_bollinger_bands_percent_b_places_latest_close_between_bands():
    close = pd.Series(range(1, 21), dtype=float)
    _, upper, lower, _, percent_b = calculate_bollinger_bands(close, period=20)

    expected = (close.iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
    assert percent_b.iloc[-1] == pytest.approx(expected)


def test_calculate_bollinger_bands_bandwidth_is_percent_of_middle_band():
    close = pd.Series(range(1, 21), dtype=float)
    middle, upper, lower, bandwidth, _ = calculate_bollinger_bands(close, period=20)

    expected = ((upper.iloc[-1] - lower.iloc[-1]) / middle.iloc[-1]) * 100
    assert bandwidth.iloc[-1] == pytest.approx(expected)


def test_calculate_atr_has_nan_before_period_is_available():
    high = pd.Series([11.0] * 14)
    low = pd.Series([9.0] * 14)
    close = pd.Series([10.0] * 14)

    assert math.isnan(calculate_atr(high, low, close, period=14).iloc[12])


def test_calculate_atr_uses_high_low_range_when_there_are_no_gaps():
    high = pd.Series([11.0] * 14)
    low = pd.Series([9.0] * 14)
    close = pd.Series([10.0] * 14)

    assert calculate_atr(high, low, close, period=14).iloc[-1] == 2.0


def test_calculate_atr_includes_gap_up_true_range():
    high = pd.Series([11.0] * 13 + [20.0])
    low = pd.Series([9.0] * 13 + [19.0])
    close = pd.Series([10.0] * 14)

    assert calculate_atr(high, low, close, period=14).iloc[-1] == pytest.approx((13 * 2 + 10) / 14)


def test_calculate_atr_includes_gap_down_true_range():
    high = pd.Series([11.0] * 13 + [1.0])
    low = pd.Series([9.0] * 13 + [0.0])
    close = pd.Series([10.0] * 14)

    assert calculate_atr(high, low, close, period=14).iloc[-1] == pytest.approx((13 * 2 + 10) / 14)


def test_calculate_ema_starts_at_first_close():
    ema = calculate_ema(pd.Series([10.0, 20.0]), period=3)

    assert ema.iloc[0] == 10.0


def test_calculate_ema_stays_constant_for_constant_prices():
    ema = calculate_ema(pd.Series([7.0] * 10), period=3)

    assert ema.iloc[-1] == 7.0


def test_calculate_ema_matches_manual_period_three_example():
    ema = calculate_ema(pd.Series([10.0, 14.0, 18.0]), period=3)

    assert ema.iloc[-1] == 15.0


def test_detect_latest_ema_crossover_returns_insufficient_data_for_single_close():
    assert detect_latest_ema_crossover(pd.Series([10.0])) == "insufficient_data"


def test_detect_latest_ema_crossover_detects_bullish_cross():
    close = pd.Series([10.0] * 30 + [20.0])

    assert detect_latest_ema_crossover(close) == "bullish"


def test_detect_latest_ema_crossover_detects_bearish_cross():
    close = pd.Series([20.0] * 30 + [10.0])

    assert detect_latest_ema_crossover(close) == "bearish"


def test_detect_latest_ema_crossover_returns_none_without_fresh_cross():
    close = pd.Series(range(1, 60), dtype=float)

    assert detect_latest_ema_crossover(close) == "none"


def test_build_technical_summary_raises_when_market_data_is_insufficient():
    with pytest.raises(ValueError, match="Not enough market data"):
        build_technical_summary(make_ohlcv_frame(rows=49))


def test_build_technical_summary_includes_core_response_fields_and_tail_candles():
    summary = build_technical_summary(make_ohlcv_frame())

    assert summary["bars_returned"] == 260
    assert summary["as_of"] == "2024-09-16"
    assert len(summary["candles_tail"]) == 10


def test_build_technical_summary_includes_new_volatility_fields():
    summary = build_technical_summary(make_ohlcv_frame())

    assert summary["volatility"]["atr_14"] is not None
    assert summary["volatility"]["bollinger_upper"] is not None
    assert summary["volatility"]["bollinger_lower"] is not None


def test_build_technical_summary_marks_bullish_moving_average_alignment_for_uptrend():
    summary = build_technical_summary(make_ohlcv_frame())

    assert summary["trend"]["ma_alignment"] == "bullish"


def test_build_technical_summary_warns_when_52_week_history_is_unavailable():
    summary = build_technical_summary(make_ohlcv_frame(rows=100))

    assert "52-week high/low metrics are unavailable" in summary["data_warnings"][0]


def test_build_summary_text_mentions_new_ema_and_atr_signals():
    summary = build_technical_summary(make_ohlcv_frame())
    text = build_summary_text(summary)

    assert "EMA crossover" in text
    assert "ATR(14)" in text
