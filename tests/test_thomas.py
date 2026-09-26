"""Thomas 解求值：单调性、符号方向、半穿透点与数值稳定性。"""

import pytest

from app import thomas
from app.presets import SOFTENING_BED_CONDITION as PRESET
from app.timegrid import build_time_grid, half_rise_time


def _curve(**overrides):
    params = {**PRESET, **overrides}
    times = build_time_grid(
        params["C0"], params["Q"], params["q0"], params["kTh"], params["m"]
    )
    return times, thomas.thomas_curve(times, **params)


def test_curve_climbs_monotonically_from_low_to_high():
    _, ratios = _curve()
    assert ratios[0] < 1e-3
    assert ratios[-1] > 0.999
    assert all(b >= a for a, b in zip(ratios, ratios[1:]))


def test_exponent_sign_gives_rising_not_falling_curve():
    """指数项符号写反会得到先高后低的反向曲线，这里锁住正确方向。"""
    t_half = half_rise_time(PRESET["C0"], PRESET["Q"], PRESET["q0"], PRESET["m"])
    early = thomas.thomas_relative_concentration(0.25 * t_half, **PRESET)
    late = thomas.thomas_relative_concentration(1.75 * t_half, **PRESET)
    assert early < 0.5 < late
    assert early < late


def test_half_rise_at_characteristic_time():
    t_half = half_rise_time(PRESET["C0"], PRESET["Q"], PRESET["q0"], PRESET["m"])
    ratio = thomas.thomas_relative_concentration(t_half, **PRESET)
    assert ratio == pytest.approx(0.5, abs=1e-12)


def test_logistic_decay_is_overflow_safe():
    assert thomas.logistic_decay(0.0) == pytest.approx(0.5)
    assert thomas.logistic_decay(1e6) == 0.0
    assert thomas.logistic_decay(-1e6) == 1.0


def test_steep_rate_constant_still_evaluates():
    _, ratios = _curve(kTh=1.0)
    assert ratios[0] == 0.0
    assert ratios[-1] > 0.999
    assert all(b >= a for a, b in zip(ratios, ratios[1:]))
