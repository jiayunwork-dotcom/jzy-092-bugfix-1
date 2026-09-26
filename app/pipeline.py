"""单工况穿透计算流程编排：校验 -> 时间轴 -> 曲线 -> 积分 -> 穿透判定。"""

from . import breakthrough, integrate, thomas, timegrid, validation

HALF_RISE_LEVEL = 0.5
SATURATION_RATIO_TOLERANCE = 0.99


def run_condition(data: dict) -> dict:
    """针对单一工况，把整条曲线连同派生量一次算完。"""
    params, options = validation.validate_condition(data)

    times = timegrid.build_time_grid(
        params["C0"],
        params["Q"],
        params["q0"],
        params["kTh"],
        params["m"],
        t_end=options["t_end"],
        n_points=options["n_points"],
    )
    ratios = thomas.thomas_curve(
        times, params["C0"], params["Q"], params["q0"], params["kTh"], params["m"]
    )
    cumulative = integrate.cumulative_adsorption(
        times, ratios, params["Q"], params["C0"]
    )

    threshold = options["threshold"]
    breakthrough_time = breakthrough.find_crossing_time(times, ratios, threshold)
    window = breakthrough.rise_window(times, ratios)

    t_half = timegrid.half_rise_time(
        params["C0"], params["Q"], params["q0"], params["m"]
    )
    theoretical_capacity = params["q0"] * params["m"]
    total_adsorbed = cumulative[-1]
    saturation_ratio = total_adsorbed / theoretical_capacity

    # 曲线必须已越过半程、且累计吸附足够接近理论容量，才允许判定饱和；
    # 曲线还没越过半程时绝不能宣称已经饱和。
    crossed_half_rise = ratios[-1] >= HALF_RISE_LEVEL
    saturated = (
        crossed_half_rise and saturation_ratio >= SATURATION_RATIO_TOLERANCE
    )

    return {
        "input": params,
        "threshold": threshold,
        "n_points": len(times),
        "t_end": times[-1],
        "time": times,
        "relative_concentration": ratios,
        "cumulative_adsorbed": cumulative,
        "breakthrough_time": breakthrough_time,
        "half_rise_time": t_half,
        "rise_window": window,
        "total_adsorbed": total_adsorbed,
        "theoretical_capacity": theoretical_capacity,
        "saturation_ratio": saturation_ratio,
        "saturated": saturated,
    }
