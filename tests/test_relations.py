"""参数变化规律：容量加倍推后穿透、流量加倍提前穿透、
速率常数调大曲线变陡、进料浓度为零报错、累计吸附守恒。"""

import pytest

from app import pipeline
from app.presets import SOFTENING_BED_CONDITION as BASE
from app.validation import ValidationError


def _run(**overrides):
    return pipeline.run_condition({**BASE, **overrides})


def test_doubling_capacity_delays_breakthrough_twofold():
    """单位吸附容量加倍、其余不变，穿透时刻大致推后一倍。"""
    t1 = _run()["breakthrough_time"]
    t2 = _run(q0=BASE["q0"] * 2.0)["breakthrough_time"]
    assert t2 > t1
    assert t2 / t1 == pytest.approx(2.0, rel=0.05)


def test_doubling_flow_advances_breakthrough():
    """体积流量加倍，穿透提前到来（大致减半）。"""
    t1 = _run()["breakthrough_time"]
    t2 = _run(Q=BASE["Q"] * 2.0)["breakthrough_time"]
    assert t2 < t1
    assert t2 / t1 == pytest.approx(0.5, rel=0.10)


def test_larger_rate_constant_steepens_curve():
    """速率常数调大，10% -> 90% 爬升窗口收窄、曲线变陡。"""
    w1 = _run()["rise_window"]["width"]
    w2 = _run(kTh=BASE["kTh"] * 2.0)["rise_window"]["width"]
    assert w1 is not None and w2 is not None
    assert 0.0 < w2 < w1
    assert w2 / w1 == pytest.approx(0.5, rel=0.05)


def test_zero_feed_concentration_rejected():
    with pytest.raises(ValidationError) as excinfo:
        _run(C0=0.0)
    assert any("C0" in reason for reason in excinfo.value.reasons)


def test_cumulative_adsorption_conserves_theoretical_capacity():
    """运行足够久，累计吸附量趋近理论容量 q0*m。"""
    result = _run()
    assert result["saturated"] is True
    assert result["total_adsorbed"] == pytest.approx(
        result["theoretical_capacity"], rel=0.01
    )
