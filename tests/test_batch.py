"""批量工况调度：逐条独立、错误隔离、无共享状态。"""

import pytest

from app import batch, pipeline
from app.presets import SOFTENING_BED_CONDITION as BASE
from app.validation import ValidationError

CONDITION_A = dict(BASE)
CONDITION_B = {**BASE, "Q": BASE["Q"] * 2.0}


def test_batch_results_match_independent_single_runs():
    results = batch.run_batch([CONDITION_A, CONDITION_B])
    assert [item["ok"] for item in results] == [True, True]
    assert [item["index"] for item in results] == [0, 1]
    # 与逐条单独计算完全一致：批处理不引入任何额外状态
    assert results[0]["result"] == pipeline.run_condition(CONDITION_A)
    assert results[1]["result"] == pipeline.run_condition(CONDITION_B)


def test_batch_isolates_invalid_items():
    bad = {**BASE, "C0": 0.0}
    results = batch.run_batch([CONDITION_A, bad, CONDITION_B])
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert results[2]["ok"] is True
    assert any("C0" in r for r in results[1]["error"]["reasons"])


def test_batch_calls_do_not_leak_state():
    first = batch.run_batch([CONDITION_A, CONDITION_B])
    second = batch.run_batch([CONDITION_B, CONDITION_A])
    # 同一工况无论排在第几位、无论之前算过什么，结果都一致
    assert first[0]["result"] == second[1]["result"]
    assert first[1]["result"] == second[0]["result"]


def test_empty_or_malformed_dataset_rejected():
    with pytest.raises(ValidationError):
        batch.run_batch([])
    with pytest.raises(ValidationError):
        batch.run_batch("not-a-list")
