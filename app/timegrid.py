"""时间轴离散模块。

默认时间网格自动覆盖到床层充分饱和：

    t_half = q0*m / (Q*C0)            —— 相对浓度达到 0.5 的特征时刻
    t_end  = t_half + TAIL/(kTh*C0)

TAIL 取 12，对应末端相对浓度约 1 - 6e-6，足以支撑饱和判定与
累计吸附量守恒校验。调用方也可显式指定 t_end 与 n_points。

默认采样采用沿指数坐标

    u(t) = kTh*(q0*m/Q - C0*t)

分段等距的自适应网格：Thomas 解在 u 坐标下形状固定
（C/C0 = 1/(1+exp(u))），而在时间坐标下，速率常数越大、床层越大，
前沿占整条时间轴的比例越小，单一等距网格会把前沿量化成一两个步长，
导致爬升窗口与穿透插值失真。自适应网格在前沿段密集采样（保证
10%–90% 爬升带内有足够多的点），前沿之前与饱和尾部粗采样即可。

调用方显式给出 t_end 或 n_points 时，仍使用 [0, t_end] 上的等距网格。
"""

import math

TAIL_EXPONENT = 12.0
DEFAULT_N_POINTS = 400
MAX_N_POINTS = 20000

# 自适应默认网格的采样参数（沿 u 坐标）。
FRONT_BAND_INTERVALS = 40
"""10%–90% 爬升带（u 从 ln9 到 -ln9）内的采样间隔数，密集段步长据此确定。"""
PRE_REGION_INTERVALS = 40
"""前沿之前（近乎零浓度平台）的粗采样间隔数。"""
TAIL_REGION_STEP_EXPONENT = 0.4
"""饱和尾部粗采样在 u 坐标上的步长上限。"""
FRONT_MARGIN_EXPONENT = 8.0
"""密集段自半穿透点向两侧延伸的默认半宽（u 单位），足以包住 5% 阈值穿越。"""
THRESHOLD_MARGIN_EXPONENT = 2.0
"""自定义阈值时，密集段边界在阈值穿越点外侧再让出的余量。"""
MAX_FRONT_HALF_WIDTH = 40.0
"""密集段半宽上限：再低的阈值，其穿越点也不会精确解析（阈值已近于 0），
同时保证任意合法输入下总点数有界、不发生 inf 参与的取整溢出。"""
DEFAULT_THRESHOLD = 0.05

_LN_9 = math.log(9.0)


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
    threshold: float = DEFAULT_THRESHOLD,
) -> list[float]:
    """生成时间网格（含 t=0 与终止端点）。

    显式给出 t_end 或 n_points 时，返回 [0, t_end] 上的等距网格；
    两者均缺省时，返回沿指数坐标分段等距的自适应默认网格。
    """
    if t_end is None and n_points is None:
        return _build_adaptive_grid(C0, Q, q0, kTh, m, threshold)
    return _build_uniform_grid(C0, Q, q0, kTh, m, t_end, n_points)


def _build_uniform_grid(
    C0: float,
    Q: float,
    q0: float,
    kTh: float,
    m: float,
    t_end: float | None,
    n_points: int | None,
) -> list[float]:
    """[0, t_end] 上的等距时间网格（含两端点）。"""
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


def _build_adaptive_grid(
    C0: float,
    Q: float,
    q0: float,
    kTh: float,
    m: float,
    threshold: float,
) -> list[float]:
    """沿 u 坐标分段等距的自适应网格，映射回时间轴。

    三段：前沿之前的零浓度平台（粗）、密集前沿段（细）、饱和尾部（粗）。
    起点 u0 = kTh*q0*m/Q 对应 t=0，末端 -TAIL_EXPONENT 对应默认 t_end。
    """
    a = kTh * C0
    u0 = kTh * q0 * m / Q

    # 密集段半宽：盖住阈值穿越点并留出余量；阈值取默认值时至少外推到 8，
    # 保证 10%–90% 爬升带与 5% 穿越点之外仍有足够缓冲。阈值极低时
    # （穿越点比饱和尾部 u=-TAIL 更远）密集段照常前伸，默认 t_end 随之推后，
    # 饱和尾部仍从 -front_half_width 延伸到 -TAIL。封顶 40 以防近零阈值
    # 造成点数失控或 inf 取整溢出。
    if threshold <= 0.0:
        threshold_u = 0.0
    else:
        ratio = (1.0 - threshold) / threshold
        threshold_u = math.log(ratio) if math.isfinite(ratio) else MAX_FRONT_HALF_WIDTH
    front_half_width = min(
        MAX_FRONT_HALF_WIDTH,
        max(FRONT_MARGIN_EXPONENT, threshold_u + THRESHOLD_MARGIN_EXPONENT),
    )

    # 密集段步长：10%–90% 带（宽 2*ln9）内至少 FRONT_BAND_INTERVALS 个间隔。
    du_dense = 2.0 * _LN_9 / FRONT_BAND_INTERVALS

    u_front_hi = min(front_half_width, u0)  # t>=0 时 u 不会超过 u0
    u_front_lo = -front_half_width
    u_end = -TAIL_EXPONENT

    us: list[float] = []

    def add(u: float) -> None:
        if not us or u != us[-1]:
            us.append(u)

    # 前沿之前：u0 -> +A（仅当 t=0 已在密集段之外），零浓度平台粗采样。
    if u0 > front_half_width:
        for k in range(PRE_REGION_INTERVALS + 1):
            add(u0 - k * (u0 - front_half_width) / PRE_REGION_INTERVALS)

    # 密集前沿段：+A -> -A。
    if u_front_hi > u_front_lo:
        n_dense = max(1, math.ceil((u_front_hi - u_front_lo) / du_dense))
        for k in range(n_dense + 1):
            add(u_front_hi - k * (u_front_hi - u_front_lo) / n_dense)
    else:
        add(u_front_hi)

    # 饱和尾部：-A -> -TAIL（A 已到 TAIL 时本段为空）。
    if u_front_lo > u_end:
        n_tail = max(
            1, math.ceil((u_front_lo - u_end) / TAIL_REGION_STEP_EXPONENT)
        )
        for k in range(1, n_tail + 1):
            add(u_front_lo - k * (u_front_lo - u_end) / n_tail)

    # u 递减 -> t 递增；t(u) = (u0 - u)/(kTh*C0)，自动保证 t[0]=0。
    return [(u0 - u) / a for u in us]
