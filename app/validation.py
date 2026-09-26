"""输入校验模块。

C0、Q、q0、kTh、m 五个工况参数必须全部为正有限数值；
threshold、t_end、n_points 为可选参数，同样带范围检查。
所有校验失败都以携带全部原因的 ValidationError 抛出。
"""

import math

from .timegrid import MAX_N_POINTS

REQUIRED_POSITIVE_FIELDS = ("C0", "Q", "q0", "kTh", "m")
DEFAULT_THRESHOLD = 0.05


class ValidationError(Exception):
    """携带全部失败原因的输入校验错误。"""

    def __init__(self, reasons):
        self.reasons = [str(r) for r in reasons]
        super().__init__("；".join(self.reasons))


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_condition(data) -> tuple[dict, dict]:
    """校验单一工况，返回 (params, options)。

    params  含 C0、Q、q0、kTh、m 五个正数；
    options 含 threshold、t_end、n_points（后两者缺省为 None，表示自动）。
    """
    if not isinstance(data, dict):
        raise ValidationError(
            [f"请求体必须是 JSON 对象（收到 {type(data).__name__}）"]
        )

    reasons: list[str] = []
    params: dict[str, float] = {}
    for name in REQUIRED_POSITIVE_FIELDS:
        if name not in data:
            reasons.append(f"缺少必需参数 {name}")
            continue
        raw = data[name]
        if not _is_number(raw):
            reasons.append(f"参数 {name} 必须是数值（收到 {raw!r}）")
            continue
        value = float(raw)
        if not math.isfinite(value):
            reasons.append(f"参数 {name} 必须是有限数值（收到 {raw!r}）")
            continue
        if value <= 0.0:
            reasons.append(f"参数 {name} 必须为正数（收到 {value}）")
            continue
        params[name] = value

    options: dict = {}

    threshold = data.get("threshold", DEFAULT_THRESHOLD)
    if not _is_number(threshold) or not 0.0 < float(threshold) < 1.0:
        reasons.append(f"参数 threshold 必须在 (0, 1) 区间内（收到 {threshold!r}）")
    else:
        options["threshold"] = float(threshold)

    t_end = data.get("t_end")
    if t_end is None:
        options["t_end"] = None
    elif not _is_number(t_end) or float(t_end) <= 0.0:
        reasons.append(f"参数 t_end 必须为正数（收到 {t_end!r}）")
    else:
        options["t_end"] = float(t_end)

    n_points = data.get("n_points")
    if n_points is None:
        options["n_points"] = None
    elif not _is_number(n_points) or float(n_points) != int(float(n_points)):
        reasons.append(f"参数 n_points 必须是整数（收到 {n_points!r}）")
    elif int(float(n_points)) < 2:
        reasons.append(f"参数 n_points 必须 >= 2（收到 {n_points!r}）")
    elif int(float(n_points)) > MAX_N_POINTS:
        reasons.append(f"参数 n_points 不能超过 {MAX_N_POINTS}（收到 {n_points!r}）")
    else:
        options["n_points"] = int(float(n_points))

    if reasons:
        raise ValidationError(reasons)
    return params, options
