"""穿透时刻判定与爬升窗口模块。

穿透时刻取相对浓度首次跨过约定阈值的时间（相邻采样点间线性插值）。
爬升窗口（默认 10% -> 90%）用于刻画曲线陡峭程度。
"""


def find_crossing_time(
    times: list[float], ratios: list[float], threshold: float
) -> float | None:
    """相对浓度首次达到 threshold 的时刻；网格内未越过则返回 None。"""
    for i in range(len(times)):
        if ratios[i] >= threshold:
            if i == 0:
                return times[0]
            t0, t1 = times[i - 1], times[i]
            r0, r1 = ratios[i - 1], ratios[i]
            if r1 == r0:
                return t1
            frac = (threshold - r0) / (r1 - r0)
            return t0 + frac * (t1 - t0)
    return None


def rise_window(
    times: list[float], ratios: list[float], low: float = 0.1, high: float = 0.9
) -> dict:
    """相对浓度从 low 爬到 high 的时间窗；任一未越过则 width 为 None。"""
    t_low = find_crossing_time(times, ratios, low)
    t_high = find_crossing_time(times, ratios, high)
    width = None if (t_low is None or t_high is None) else t_high - t_low
    return {
        "low": low,
        "high": high,
        "t_low": t_low,
        "t_high": t_high,
        "width": width,
    }
