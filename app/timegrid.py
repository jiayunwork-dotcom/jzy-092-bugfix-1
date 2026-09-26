"""时间轴离散模块。

默认时间网格自动覆盖到床层充分饱和：

    t_half = q0*m / (Q*C0)            —— 相对浓度达到 0.5 的特征时刻
    t_end  = t_half + TAIL/(kTh*C0)

TAIL 取 12，对应末端相对浓度约 1 - 6e-6，足以支撑饱和判定与
累计吸附量守恒校验。

Thomas 前沿的宽度正比于 1/(kTh*C0)，与 t_half 无关：速率常数越大、
床装得越多，前沿相对整条时间轴就越窄。[0, t_end] 上固定点数的均匀
网格无法兼顾两者——点距一旦被 t_half 撑大，10% -> 90% 爬升段里可能
只剩一两个采样点，穿透时刻与爬升窗口就会被网格步长绑架（调大
kTh 窗口反而变宽、穿透反而提前之类的假象都由此而来）。

因此默认请求（t_end 与 n_points 都缺省）使用分段网格：前沿两侧按
指数坐标 u = kTh*C0*(t_half - t) 均匀加密，保证爬升段内始终有足够
采样点；前沿前后的平淡段稀疏取样，总点数与工况无关。调用方显式
给出 t_end 或 n_points 时，仍退回原来的均匀网格，采样行为不变。
"""

import math

TAIL_EXPONENT = 12.0
DEFAULT_N_POINTS = 400
MAX_N_POINTS = 20000

# 10% -> 90% 爬升窗口在指数坐标 u 下的半宽：ln(0.9/0.1)
RISE_WINDOW_HALF_EXPONENT = math.log(9.0)
# 加密区在指数坐标下的半宽：覆盖相对浓度约 3.4e-4 -> 0.99966 的区段，
# 默认阈值 0.05（u ≈ 2.94）及常用阈值都落在加密区内
DENSE_HALF_EXPONENT = 8.0
# 10% -> 90% 窗口内的目标采样点数（为"至少 20 个点"留出余量）
RISE_WINDOW_SAMPLES = 25
# 前沿前、后平淡段的稀疏采样点数
HEAD_N_POINTS = 64
TAIL_N_POINTS = 32


def half_rise_time(C0: float, Q: float, q0: float, m: float) -> float:
    """相对浓度达到 0.5 的特征时刻 q0*m/(Q*C0)。"""
    return q0 * m / (Q * C0)


def default_t_end(C0: float, Q: float, q0: float, kTh: float, m: float) -> float:
    """默认终止时刻：半穿透时刻再加一段足以饱和的尾部。"""
    return half_rise_time(C0, Q, q0, m) + TAIL_EXPONENT / (kTh * C0)


def _linspace(start: float, stop: float, n: int) -> list[float]:
    """[start, stop] 上 n 个等距点（含两端点）。"""
    if n == 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]


def _default_dense_grid(
    C0: float, Q: float, q0: float, kTh: float, m: float
) -> list[float]:
    """默认请求的分段网格：前沿加密、两端稀疏，总点数与工况无关。"""
    t_half = half_rise_time(C0, Q, q0, m)
    end = default_t_end(C0, Q, q0, kTh, m)
    rate = kTh * C0  # 指数坐标 u 随时间的变化率

    dense_half = DENSE_HALF_EXPONENT / rate
    dense_lo = max(0.0, t_half - dense_half)
    dense_hi = min(end, t_half + dense_half)

    # 加密区点距：让 10% -> 90% 窗口内约落 RISE_WINDOW_SAMPLES 个点
    window = 2.0 * RISE_WINDOW_HALF_EXPONENT / rate
    step = window / RISE_WINDOW_SAMPLES
    n_dense = max(2, math.ceil((dense_hi - dense_lo) / step) + 1)

    grid: list[float] = []
    if dense_lo > 0.0:
        grid += _linspace(0.0, dense_lo, HEAD_N_POINTS)[:-1]
    grid += _linspace(dense_lo, dense_hi, n_dense)
    if dense_hi < end:
        grid += _linspace(dense_hi, end, TAIL_N_POINTS)[1:]
    return grid


def build_time_grid(
    C0: float,
    Q: float,
    q0: float,
    kTh: float,
    m: float,
    t_end: float | None = None,
    n_points: int | None = None,
) -> list[float]:
    """生成时间网格。

    t_end 与 n_points 都缺省时返回前沿加密的默认网格；任一被显式
    给出时退回 [0, t_end] 上的等距网格（含两端点），与历史行为一致。
    """
    if t_end is None and n_points is None:
        return _default_dense_grid(C0, Q, q0, kTh, m)
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
