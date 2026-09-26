"""穿透时刻判定：阈值跨越插值、未越过与爬升窗口。"""

import pytest

from app.breakthrough import find_crossing_time, rise_window


def test_crossing_time_interpolates_linearly():
    times = [0.0, 1.0, 2.0, 3.0]
    ratios = [0.0, 0.4, 0.6, 1.0]
    assert find_crossing_time(times, ratios, 0.5) == pytest.approx(1.5)


def test_crossing_time_returns_none_when_never_reached():
    times = [0.0, 1.0, 2.0]
    ratios = [0.0, 0.1, 0.2]
    assert find_crossing_time(times, ratios, 0.5) is None


def test_crossing_at_first_point():
    assert find_crossing_time([0.0, 1.0], [0.6, 0.9], 0.5) == 0.0


def test_rise_window_width():
    times = [0.0, 1.0, 2.0, 3.0, 4.0]
    ratios = [0.0, 0.1, 0.5, 0.9, 1.0]
    window = rise_window(times, ratios, low=0.1, high=0.9)
    assert window["t_low"] == pytest.approx(1.0)
    assert window["t_high"] == pytest.approx(3.0)
    assert window["width"] == pytest.approx(2.0)


def test_rise_window_none_when_not_crossed():
    window = rise_window([0.0, 1.0], [0.0, 0.05])
    assert window["width"] is None
