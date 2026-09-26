"""批量工况调度模块。

把一批工况作为一个数据集逐条推入计算内核，每条独立调用单工况流程：
各工况之间的中间状态互不累加、互不覆盖；单条工况校验失败只影响该条，
不中断整批。
"""

from . import pipeline, validation


def run_batch(conditions) -> list[dict]:
    """逐条计算工况数据集，按原顺序返回每条的结果或错误。"""
    if not isinstance(conditions, list) or len(conditions) == 0:
        raise validation.ValidationError(["工况数据集 runs 必须是非空数组"])

    results: list[dict] = []
    for index, condition in enumerate(conditions):
        try:
            result = pipeline.run_condition(condition)
        except validation.ValidationError as exc:
            results.append(
                {
                    "index": index,
                    "ok": False,
                    "error": {"message": str(exc), "reasons": exc.reasons},
                }
            )
        else:
            results.append({"index": index, "ok": True, "result": result})
    return results
