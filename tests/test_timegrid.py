"""时间轴离散：网格形状、默认终止时刻与非法参数。"""

import pytest

from app.presets import SOFTENING_BED_CONDITION as PRESET
from app.timegrid import (
    TAIL_EXPONENT,
    build_time_grid,
    default_t_end,
    half_rise_time,
)


def test_grid_is_uniform_and_spans_endpoints():
    grid = build_time_grid(**PRESET, n_points=101)
    assert len(grid) == 101
    assert grid[0] == 0.0
    assert grid[-1] == pytest.approx(default_t_end(**PRESET))
    steps = {round(b - a, 9) for a, b in zip(grid, grid[1:])}
    assert len(steps) == 1


def test_default_grid_covers_half_rise_and_saturation_tail():
    t_half = half_rise_time(PRESET["C0"], PRESET["Q"], PRESET["q0"], PRESET["m"])
    end = default_t_end(**PRESET)
    assert end > t_half
    assert end - t_half == pytest.approx(TAIL_EXPONENT / (PRESET["kTh"] * PRESET["C0"]))


def test_explicit_t_end_is_respected():
    grid = build_time_grid(**PRESET, t_end=100.0, n_points=11)
    assert grid[-1] == pytest.approx(100.0)


def test_invalid_grid_parameters_raise():
    with pytest.raises(ValueError):
        build_time_grid(**PRESET, n_points=1)
    with pytest.raises(ValueError):
        build_time_grid(**PRESET, t_end=0.0)
    with pytest.raises(ValueError):
        build_time_grid(**PRESET, t_end=-5.0)
