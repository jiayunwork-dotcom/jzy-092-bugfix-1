"""浓度亏量的数值积分模块（标准库手写梯形公式，不依赖科学计算库）。

出水相对进料的浓度亏量为 1 - C(t)/C0，累计吸附量：

    M(t) = Q * C0 * ∫0^t (1 - C(τ)/C0) dτ

运行足够久、床层接近饱和时，M(t) 趋近理论容量 q0*m。
"""


def cumulative_trapezoid(times: list[float], values: list[float]) -> list[float]:
    """累积梯形积分，返回与 times 等长的序列（首元素为 0）。"""
    if len(times) != len(values):
        raise ValueError("times 与 values 长度必须一致")
    out = [0.0]
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        out.append(out[-1] + 0.5 * (values[i - 1] + values[i]) * dt)
    return out


def cumulative_adsorption(
    times: list[float], ratios: list[float], Q: float, C0: float
) -> list[float]:
    """由相对浓度曲线求累计吸附量序列 M(t)。"""
    deficits = [1.0 - r for r in ratios]
    return [Q * C0 * area for area in cumulative_trapezoid(times, deficits)]
