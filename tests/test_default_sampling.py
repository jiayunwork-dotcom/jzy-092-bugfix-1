"""默认采样的前沿分辨率：爬升段点数、窗口与穿透时刻的解析一致性。

锁定工艺组上报的两组复现（只传五个工况参数、其余全走默认）：

1. m=5000，kTh 从 0.02 逐级调到 0.4 —— 10% -> 90% 爬升窗口应随 kTh
   增大单调收窄、翻倍大致减半，穿透时刻单调推后；
2. m=50000，kTh 从 0.002 调到 0.004 —— 穿透时刻应向半穿透点收拢
   （6656.9 -> 6661.8），窗口减半。

同时锁住：默认请求下返回曲线在 10% -> 90% 爬升段内至少有 20 个采样点；
窗口宽度与穿透时刻都能由返回曲线上的点独立插值复核出同一个数。
"""

import math

import pytest

from app import batch, pipeline
from app.presets import SOFTENING_BED_CONDITION as BASE
from app.server import create_app
from app.timegrid import MAX_N_POINTS, build_time_grid, default_t_end

WINDOW_LOW = 0.1
WINDOW_HIGH = 0.9
DEFAULT_THRESHOLD = 0.05
MIN_RISE_POINTS = 20

# 第一组复现：只调速率常数
RATE_SWEEP = [0.02, 0.05, 0.1, 0.2, 0.4]
# 第二组复现：大床 + 速率常数翻倍
LARGE_BED = {"m": 50000.0}


def _analytic_window(params):
    """Thomas 解 10% -> 90% 爬升窗口宽度：2*ln(9)/(kTh*C0)。"""
    return 2.0 * math.log(9.0) / (params["kTh"] * params["C0"])


def _analytic_crossing(params, level):
    """Thomas 解相对浓度达到 level 的时刻：t_half - ln((1-level)/level)/(kTh*C0)。"""
    t_half = params["q0"] * params["m"] / (params["Q"] * params["C0"])
    return t_half - math.log((1.0 - level) / level) / (params["kTh"] * params["C0"])


def _crossing_from_curve(times, ratios, level):
    """独立复现：在返回曲线上线性插值求 level 的首次穿越时刻。"""
    for i in range(len(times)):
        if ratios[i] >= level:
            if i == 0:
                return times[0]
            t0, t1 = times[i - 1], times[i]
            r0, r1 = ratios[i - 1], ratios[i]
            return t0 + (level - r0) * (t1 - t0) / (r1 - r0)
    return None


def _rise_point_count(result):
    """返回曲线中相对浓度落在 10% -> 90% 爬升段内的采样点数。"""
    return sum(
        1 for r in result["relative_concentration"] if WINDOW_LOW <= r <= WINDOW_HIGH
    )


def _reproduction_conditions():
    return (
        [{**BASE, "kTh": k} for k in RATE_SWEEP]
        + [{**BASE, **LARGE_BED, "kTh": 0.002}, {**BASE, **LARGE_BED, "kTh": 0.004}]
    )


def test_default_grid_packs_points_near_the_front():
    """默认网格：覆盖到饱和尾段，且前沿附近点距远小于平淡段。"""
    grid = build_time_grid(**BASE)
    assert grid[0] == 0.0
    assert grid[-1] == pytest.approx(default_t_end(**BASE))
    assert all(b > a for a, b in zip(grid, grid[1:]))
    t_half = BASE["q0"] * BASE["m"] / (BASE["Q"] * BASE["C0"])
    near = [
        b - a
        for a, b in zip(grid, grid[1:])
        if abs((a + b) / 2.0 - t_half) < 5.0
    ]
    far = [b - a for a, b in zip(grid, grid[1:]) if (a + b) / 2.0 < t_half - 100.0]
    assert near and far
    assert max(near) < 0.1 * min(far)


@pytest.mark.parametrize(
    "overrides",
    [{}, {"kTh": 0.02}, {"kTh": 0.4}, {**LARGE_BED, "kTh": 0.002}, {**LARGE_BED, "kTh": 0.004},
     {"kTh": 0.4, "m": 50000.0}],
    ids=["reference", "kTh=0.02", "kTh=0.4", "bed-kTh=0.002", "bed-kTh=0.004", "extreme"],
)
def test_default_curve_has_enough_points_in_rise_segment(overrides):
    """默认请求下，无论速率常数多大、床装多大，爬升段内至少 20 个点。"""
    result = pipeline.run_condition({**BASE, **overrides})
    assert _rise_point_count(result) >= MIN_RISE_POINTS
    assert result["n_points"] <= MAX_N_POINTS


def test_rate_sweep_window_and_breakthrough_track_thomas_solution():
    """第一组复现：窗口随 kTh 单调收窄（相对误差 <= 1%），穿透单调推后。"""
    windows, breakthroughs = [], []
    for kTh in RATE_SWEEP:
        params = {**BASE, "kTh": kTh}
        result = pipeline.run_condition(params)
        window = result["rise_window"]["width"]
        assert window == pytest.approx(_analytic_window(params), rel=0.01)
        bt = result["breakthrough_time"]
        assert abs(bt - _analytic_crossing(params, DEFAULT_THRESHOLD)) <= (
            0.05 * _analytic_window(params)
        )
        windows.append(window)
        breakthroughs.append(bt)
    assert all(w2 < w1 for w1, w2 in zip(windows, windows[1:]))
    assert all(b2 > b1 for b1, b2 in zip(breakthroughs, breakthroughs[1:]))
    # 速率常数翻倍，窗口大致减半（0.02 -> 0.05 不是翻倍，从第二对起检查）
    for w1, w2 in zip(windows[1:], windows[2:]):
        assert w2 / w1 == pytest.approx(0.5, rel=0.02)


def test_doubling_rate_constant_halves_window():
    w1 = pipeline.run_condition({**BASE, "kTh": 0.1})["rise_window"]["width"]
    w2 = pipeline.run_condition({**BASE, "kTh": 0.2})["rise_window"]["width"]
    assert w2 / w1 == pytest.approx(0.5, rel=0.02)


def test_large_bed_breakthrough_recedes_toward_half_rise():
    """第二组复现：m=50000，kTh 0.002 -> 0.004，穿透 6656.9 -> 6661.8。"""
    slow = pipeline.run_condition({**BASE, **LARGE_BED, "kTh": 0.002})
    fast = pipeline.run_condition({**BASE, **LARGE_BED, "kTh": 0.004})
    assert slow["breakthrough_time"] == pytest.approx(6656.9, abs=0.1)
    assert fast["breakthrough_time"] == pytest.approx(6661.8, abs=0.1)
    assert fast["breakthrough_time"] > slow["breakthrough_time"]
    assert slow["rise_window"]["width"] / fast["rise_window"]["width"] == pytest.approx(
        2.0, rel=0.02
    )


def test_reported_quantities_recomputable_from_returned_curve():
    """穿透时刻与爬升窗口必须能由返回曲线上的点独立插值复核。"""
    for params in _reproduction_conditions():
        result = pipeline.run_condition(params)
        times, ratios = result["time"], result["relative_concentration"]
        bt = _crossing_from_curve(times, ratios, result["threshold"])
        assert bt == pytest.approx(result["breakthrough_time"], rel=1e-9)
        t_low = _crossing_from_curve(times, ratios, WINDOW_LOW)
        t_high = _crossing_from_curve(times, ratios, WINDOW_HIGH)
        assert t_high - t_low == pytest.approx(
            result["rise_window"]["width"], rel=1e-9
        )


def test_reference_condition_stays_on_mark():
    """参考工况：穿透仍在 656.8 附近（偏差 <= 0.1），累计吸附收到理论容量。"""
    result = pipeline.run_condition(BASE)
    assert result["breakthrough_time"] == pytest.approx(656.8, abs=0.1)
    assert result["total_adsorbed"] == pytest.approx(
        result["theoretical_capacity"], rel=0.01
    )
    assert result["saturated"] is True


def test_batch_and_single_endpoints_agree_on_reproduction_conditions():
    """单条与批量接口对同一工况给出完全一致的结果。"""
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    conditions = _reproduction_conditions()
    resp = client.post("/api/v1/breakthrough/batch", json={"runs": conditions})
    assert resp.status_code == 200
    items = resp.get_json()["results"]
    assert all(item["ok"] for item in items)
    for condition, item in zip(conditions, items):
        single = client.post("/api/v1/breakthrough/run", json=condition).get_json()
        assert item["result"] == single


def test_explicit_sampling_is_left_untouched():
    """显式给定 t_end 与 n_points：按调用方的采样来，不做前沿加密。"""
    result = pipeline.run_condition({**BASE, "t_end": 700.0, "n_points": 51})
    assert result["n_points"] == 51
    assert result["time"][-1] == pytest.approx(700.0)
    steps = {round(b - a, 9) for a, b in zip(result["time"], result["time"][1:])}
    assert len(steps) == 1
