"""默认网格的前沿分辨率：锁住工艺组复现的两组问题。

- 默认请求下，无论速率常数多大、床装多大，10%–90% 爬升带内至少 20 个点；
- 爬升窗口与 Thomas 解析解相对误差 <= 1%，翻倍 kTh 时窗口大致减半；
- 穿透时刻与解析值偏差 <= 同工况窗口宽度的 5%，且随 kTh 单调推后；
- 上述量都能从返回曲线上自行线性插值复核；
- 单条与批量对同一工况完全一致；
- 显式给出 t_end / n_points 时仍是原来的等距采样。
"""

import math

import pytest

from app import batch, pipeline, timegrid
from app.presets import SOFTENING_BED_CONDITION as BASE

LN_9 = math.log(9.0)


def analytic_window(kTh, C0=BASE["C0"]):
    """Thomas 解的 10%–90% 爬升窗宽度：2*ln9/(kTh*C0)。"""
    return 2.0 * LN_9 / (kTh * C0)


def analytic_breakthrough(kTh, q0, m, Q=BASE["Q"], C0=BASE["C0"], threshold=0.05):
    """Thomas 解的阈值穿越时刻：t_half - ln((1-p)/p)/(kTh*C0)。"""
    t_half = q0 * m / (Q * C0)
    return t_half - math.log((1.0 - threshold) / threshold) / (kTh * C0)


def interp_crossing(times, ratios, level):
    """从返回曲线上线性插值读 level 的穿越时刻，与服务内部读法一致。"""
    for i in range(1, len(times)):
        if ratios[i] >= level:
            r0, r1 = ratios[i - 1], ratios[i]
            frac = (level - r0) / (r1 - r0)
            return times[i - 1] + frac * (times[i] - times[i - 1])
    return None


def curve_window(result):
    times, ratios = result["time"], result["relative_concentration"]
    t10 = interp_crossing(times, ratios, 0.1)
    t90 = interp_crossing(times, ratios, 0.9)
    assert t10 is not None and t90 is not None
    return t90 - t10


def band_point_count(result):
    return sum(1 for r in result["relative_concentration"] if 0.1 < r < 0.9)


RATE_CONSTANTS = [0.002, 0.02, 0.05, 0.1, 0.2, 0.4]


@pytest.mark.parametrize("kTh", RATE_CONSTANTS)
def test_rise_band_has_at_least_20_points_for_any_rate_constant(kTh):
    """速率常数再大，默认曲线在一成到九成之间也至少有 20 个点。"""
    result = pipeline.run_condition({**BASE, "kTh": kTh})
    assert band_point_count(result) >= 20


@pytest.mark.parametrize("m", [5000.0, 50000.0, 500000.0])
def test_rise_band_has_at_least_20_points_for_any_bed_size(m):
    """床装得再大，默认曲线在一成到九成之间也至少有 20 个点。"""
    result = pipeline.run_condition({**BASE, "m": m})
    assert band_point_count(result) >= 20


@pytest.mark.parametrize("kTh", RATE_CONSTANTS[1:])
def test_group1_window_matches_thomas_analytic_within_1_percent(kTh):
    """复现组1：kTh 调快后窗口与 Thomas 解析值相对误差 <= 1%，
    且可直接用返回曲线上的点插值复核。"""
    result = pipeline.run_condition({**BASE, "kTh": kTh})
    width = curve_window(result)
    assert width == pytest.approx(analytic_window(kTh), rel=0.01)
    # 服务返回的窗口与调用方自行插值读到的是同一个数
    assert result["rise_window"]["width"] == pytest.approx(width, rel=1e-12)


@pytest.mark.parametrize("kTh", RATE_CONSTANTS[1:])
def test_group1_breakthrough_within_5_percent_of_window(kTh):
    """复现组1：穿透时刻与解析值的偏差不超过该工况窗口宽度的 5%。"""
    result = pipeline.run_condition({**BASE, "kTh": kTh})
    expected = analytic_breakthrough(kTh, BASE["q0"], BASE["m"])
    assert result["breakthrough_time"] == pytest.approx(
        expected, abs=0.05 * analytic_window(kTh)
    )
    # 同样能从曲线上自行插值复核
    assert interp_crossing(
        result["time"], result["relative_concentration"], result["threshold"]
    ) == pytest.approx(result["breakthrough_time"], rel=1e-12, abs=1e-12)


def test_window_halves_when_rate_constant_doubles():
    """速率常数翻倍，10%–90% 窗口大致减半（沿整档速率常数检验）。"""
    for k1, k2 in [(0.02, 0.04), (0.05, 0.1), (0.1, 0.2), (0.2, 0.4)]:
        w1 = pipeline.run_condition({**BASE, "kTh": k1})["rise_window"]["width"]
        w2 = pipeline.run_condition({**BASE, "kTh": k2})["rise_window"]["width"]
        assert 0.0 < w2 < w1
        assert w2 / w1 == pytest.approx(0.5, rel=0.01)


def test_breakthrough_monotonically_delayed_with_rate_constant():
    """速率常数增大，5% 穿透时刻单调推后（而不是乱跳或提前）。"""
    times_bt = [
        pipeline.run_condition({**BASE, "kTh": k})["breakthrough_time"]
        for k in RATE_CONSTANTS
    ]
    assert all(b > a for a, b in zip(times_bt, times_bt[1:]))


@pytest.mark.parametrize("kTh", [0.002, 0.004])
def test_group2_large_bed_matches_analytic(kTh):
    """复现组2：m=50000 时窗口与穿透时刻均贴合 Thomas 解析值；
    kTh 翻倍后穿透应略微推后（约 6656.9 -> 6661.8）而非提前。"""
    result = pipeline.run_condition({**BASE, "m": 50000.0, "kTh": kTh})
    assert band_point_count(result) >= 20
    assert curve_window(result) == pytest.approx(
        analytic_window(kTh), rel=0.01
    )
    expected = analytic_breakthrough(kTh, BASE["q0"], 50000.0)
    assert result["breakthrough_time"] == pytest.approx(
        expected, abs=0.05 * analytic_window(kTh)
    )


def test_group2_faster_constant_delays_breakthrough_on_large_bed():
    slow = pipeline.run_condition({**BASE, "m": 50000.0, "kTh": 0.002})
    fast = pipeline.run_condition({**BASE, "m": 50000.0, "kTh": 0.004})
    assert slow["breakthrough_time"] == pytest.approx(6656.9, abs=1.0)
    assert fast["breakthrough_time"] == pytest.approx(6661.8, abs=1.0)
    assert fast["breakthrough_time"] > slow["breakthrough_time"]
    # kTh 翻倍，窗口大致减半（旧实现只从 19.4 缩到 18.2）
    assert fast["rise_window"]["width"] / slow["rise_window"]["width"] == pytest.approx(
        0.5, rel=0.01
    )


def test_reference_case_breakthrough_still_near_656_8():
    """参考工况：穿透时刻仍在 656.8 附近（偏差 <= 0.1），容量照常收满。"""
    result = pipeline.run_condition(BASE)
    assert result["breakthrough_time"] == pytest.approx(656.8, abs=0.1)
    assert result["saturated"] is True
    assert result["total_adsorbed"] == pytest.approx(
        result["theoretical_capacity"], rel=0.01
    )


def test_batch_matches_single_for_reproduced_conditions():
    """两组复现工况走批量接口，与单条接口结果完全一致。"""
    conditions = [
        {**BASE, "kTh": 0.05},
        {**BASE, "kTh": 0.4},
        {**BASE, "m": 50000.0, "kTh": 0.004},
    ]
    results = batch.run_batch(conditions)
    assert [item["ok"] for item in results] == [True, True, True]
    for item, condition in zip(results, conditions):
        assert item["result"] == pipeline.run_condition(condition)


def test_explicit_n_points_keeps_uniform_sampling():
    """调用方显式给出点数时，行为保持原样：[0, t_end] 等距网格。"""
    grid = timegrid.build_time_grid(**BASE, n_points=401)
    assert len(grid) == 401
    steps = {round(b - a, 9) for a, b in zip(grid, grid[1:])}
    assert len(steps) == 1


def test_explicit_t_end_keeps_uniform_sampling():
    """调用方显式给出终止时刻时，行为保持原样：等距网格且末端取给定值。"""
    grid = timegrid.build_time_grid(**BASE, t_end=800.0, n_points=41)
    assert len(grid) == 41
    assert grid[-1] == pytest.approx(800.0)
    steps = {round(b - a, 9) for a, b in zip(grid, grid[1:])}
    assert len(steps) == 1


def test_explicit_t_end_pipeline_behavior_unchanged():
    """显式短终止时刻：未越过半程不许宣称饱和（旧行为不回归）。"""
    t_half = timegrid.half_rise_time(
        BASE["C0"], BASE["Q"], BASE["q0"], BASE["m"]
    )
    result = pipeline.run_condition({**BASE, "t_end": 0.5 * t_half})
    assert result["saturated"] is False
    assert result["breakthrough_time"] is None
