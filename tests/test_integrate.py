"""浓度亏量积分：梯形公式正确性与累计吸附守恒。"""

import pytest

from app import pipeline
from app.integrate import cumulative_adsorption, cumulative_trapezoid
from app.presets import SOFTENING_BED_CONDITION as PRESET


def test_trapezoid_integrates_constant_exactly():
    times = [0.0, 0.5, 1.0, 1.5, 2.0]
    values = [3.0] * 5
    out = cumulative_trapezoid(times, values)
    assert out[0] == 0.0
    assert out[-1] == pytest.approx(6.0)


def test_trapezoid_integrates_linear_exactly():
    times = [0.0, 0.5, 1.0, 1.5, 2.0]
    values = list(times)
    out = cumulative_trapezoid(times, values)
    assert out[-1] == pytest.approx(2.0)


def test_cumulative_adsorption_scales_with_flow_and_feed():
    times = [0.0, 1.0, 2.0]
    ratios = [0.0, 0.0, 0.0]  # 出水为零 -> 亏量全为 1
    out = cumulative_adsorption(times, ratios, Q=2.0, C0=150.0)
    assert out[-1] == pytest.approx(2.0 * 150.0 * 2.0)


def test_cumulative_adsorption_approaches_theoretical_capacity():
    """运行足够久时累计吸附量趋近理论容量 q0*m（守恒判据）。"""
    result = pipeline.run_condition(PRESET)
    theoretical = PRESET["q0"] * PRESET["m"]
    assert result["theoretical_capacity"] == pytest.approx(theoretical)
    assert result["total_adsorbed"] == pytest.approx(theoretical, rel=0.01)
    assert result["saturation_ratio"] == pytest.approx(1.0, abs=0.01)
