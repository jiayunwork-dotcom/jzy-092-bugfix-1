"""单工况流程：结果结构、饱和判定时机与预置算例行为。"""

from app import pipeline
from app.presets import SOFTENING_BED_CONDITION as PRESET
from app.timegrid import half_rise_time


def test_single_run_returns_full_result():
    result = pipeline.run_condition(PRESET)
    n = result["n_points"]
    assert len(result["time"]) == n
    assert len(result["relative_concentration"]) == n
    assert len(result["cumulative_adsorbed"]) == n
    assert result["saturated"] is True
    assert result["breakthrough_time"] is not None
    # 默认阈值 0.05 < 0.5，穿透时刻应早于半穿透时刻
    assert 0.0 < result["breakthrough_time"] < result["half_rise_time"]


def test_no_saturation_claim_before_half_rise():
    """曲线还没越过半程时，服务绝不能宣称已经饱和。"""
    t_half = half_rise_time(PRESET["C0"], PRESET["Q"], PRESET["q0"], PRESET["m"])
    result = pipeline.run_condition({**PRESET, "t_end": 0.5 * t_half})
    assert result["relative_concentration"][-1] < 0.5
    assert result["saturated"] is False
    assert result["breakthrough_time"] is None
    assert result["saturation_ratio"] < 0.99


def test_saturation_guard_bites_just_below_half_rise():
    """紧贴半程之下：累计吸附比例已超过 0.99，但曲线尚未越过半程，
    服务仍不得宣称饱和——半程守卫必须起作用。"""
    t_half = half_rise_time(PRESET["C0"], PRESET["Q"], PRESET["q0"], PRESET["m"])
    result = pipeline.run_condition({**PRESET, "t_end": 0.995 * t_half})
    assert result["relative_concentration"][-1] < 0.5
    assert result["saturation_ratio"] >= 0.99
    assert result["saturated"] is False


def test_preset_effluent_far_below_feed_before_breakthrough():
    """预置软化床算例：穿透发生之前出水浓度远低于进料浓度。"""
    result = pipeline.run_condition(PRESET)
    bt = result["breakthrough_time"]
    assert bt is not None
    pre = [
        c
        for t, c in zip(result["time"], result["relative_concentration"])
        if t < bt
    ]
    assert pre, "网格中应存在穿透前的采样点"
    assert max(pre) <= result["threshold"]
    assert result["relative_concentration"][0] < 1e-6


def test_custom_threshold_moves_breakthrough_time():
    early = pipeline.run_condition({**PRESET, "threshold": 0.01})
    late = pipeline.run_condition({**PRESET, "threshold": 0.2})
    assert early["breakthrough_time"] < late["breakthrough_time"]
