"""时间轴离散模块。

默认时间网格自动覆盖到床层充分饱和：

    t_half = q0*m / (Q*C0)            —— 相对浓度达到 0.5 的特征时刻
    t_end  = t_half + TAIL/(kTh*C0)

TAIL 取 12，对应末端相对浓度约 1 - 6e-6，足以支撑饱和判定与
累计吸附量守恒校验。调用方也可显式指定 t_end 与 n_points。
"""

TAIL_EXPONENT = 12.0
DEFAULT_N_POINTS = 400
MAX_N_POINTS = 20000


def half_rise_time(C0: float, Q: float, q0: float, m: float) -> float:
    """相对浓度达到 0.5 的特征时刻 q0*m/(Q*C0)。"""
    return q0 * m / (Q * C0)


def default_t_end(C0: float, Q: float, q0: float, kTh: float, m: float) -> float:
    """默认终止时刻：半穿透时刻再加一段足以饱和的尾部。"""
    return half_rise_time(C0, Q, q0, m) + TAIL_EXPONENT / (kTh * C0)


def build_time_grid(
    C0: float,
    Q: float,
    q0: float,
    kTh: float,
    m: float,
    t_end: float | None = None,
    n_points: int | None = None,
) -> list[float]:
    """生成 [0, t_end] 上的等距时间网格（含两端点）。"""
    n = DEFAULT_N_POINTS if n_points is None else int(n_points)
    end = default_t_end(C0, Q, q0, kTh, m) if t_end is None else float(t_end)
    if n < 2:
        raise ValueError(f"n_points 必须 >= 2（收到 {n}）")
    if n > MAX_N_POINTS:
        raise ValueError(f"n_points 不能超过 {MAX_N_POINTS}（收到 {n}）")
    if end <= 0.0:
        raise ValueError(f"t_end 必须为正数（收到 {end}）")
    step = end / (n - 1)
    return [i * step for i in range(n)]
