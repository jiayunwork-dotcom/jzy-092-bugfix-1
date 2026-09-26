"""Thomas 模型固定形式解的求值。

    C(t)/C0 = 1 / (1 + exp(kTh * (q0*m/Q - C0*t)))

指数项 kTh*(q0*m/Q - C0*t) 随时间单调减小：
t=0 时为正且通常很大（相对浓度接近 0），t -> 无穷 时趋于负无穷（相对浓度趋于 1），
因此曲线应当从低往高单调爬升。指数项符号写反会得到先高后低的反向曲线，
属于错误实现，本模块的测试专门锁住这一点。
"""

import math


def logistic_decay(x: float) -> float:
    """数值稳定地计算 1 / (1 + exp(x))，避免 exp 上溢。"""
    if x >= 0.0:
        e = math.exp(-x)
        return e / (1.0 + e)
    return 1.0 / (1.0 + math.exp(x))


def thomas_relative_concentration(
    t: float, C0: float, Q: float, q0: float, kTh: float, m: float
) -> float:
    """Thomas 解：时刻 t 的出水相对浓度 C(t)/C0。"""
    exponent = kTh * (q0 * m / Q - C0 * t)
    return logistic_decay(exponent)


def thomas_curve(
    times: list[float], C0: float, Q: float, q0: float, kTh: float, m: float
) -> list[float]:
    """沿时间轴逐点求值，返回与 times 等长的相对浓度序列。"""
    return [
        thomas_relative_concentration(t, C0, Q, q0, kTh, m) for t in times
    ]
