"""输入校验：正值约束、缺参、类型错误与可选参数范围。"""

import pytest

from app.presets import SOFTENING_BED_CONDITION as PRESET
from app.validation import (
    DEFAULT_THRESHOLD,
    ValidationError,
    validate_condition,
)


def test_valid_condition_passes_with_defaults():
    params, options = validate_condition(PRESET)
    assert params == {k: float(v) for k, v in PRESET.items()}
    assert options["threshold"] == DEFAULT_THRESHOLD
    assert options["t_end"] is None
    assert options["n_points"] is None


def test_zero_feed_concentration_rejected():
    with pytest.raises(ValidationError) as excinfo:
        validate_condition({**PRESET, "C0": 0.0})
    assert any("C0" in reason for reason in excinfo.value.reasons)


@pytest.mark.parametrize("field", ["C0", "Q", "q0", "kTh", "m"])
@pytest.mark.parametrize("bad_value", [0.0, -1.0])
def test_each_nonpositive_field_rejected(field, bad_value):
    with pytest.raises(ValidationError) as excinfo:
        validate_condition({**PRESET, field: bad_value})
    assert any(field in reason for reason in excinfo.value.reasons)


def test_missing_field_reported():
    data = {k: v for k, v in PRESET.items() if k != "m"}
    with pytest.raises(ValidationError) as excinfo:
        validate_condition(data)
    assert any("m" in reason for reason in excinfo.value.reasons)


def test_non_numeric_value_rejected():
    with pytest.raises(ValidationError) as excinfo:
        validate_condition({**PRESET, "Q": "fast"})
    assert any("Q" in reason for reason in excinfo.value.reasons)


def test_multiple_failures_collected_together():
    with pytest.raises(ValidationError) as excinfo:
        validate_condition({"C0": 0.0, "Q": -2.0})
    reasons = excinfo.value.reasons
    assert any("C0" in r for r in reasons)
    assert any("Q" in r for r in reasons)
    assert any("q0" in r for r in reasons)


def test_non_dict_body_rejected():
    with pytest.raises(ValidationError):
        validate_condition(None)
    with pytest.raises(ValidationError):
        validate_condition([1, 2, 3])


@pytest.mark.parametrize("bad_threshold", [0.0, 1.0, 1.5, -0.1])
def test_threshold_out_of_range_rejected(bad_threshold):
    with pytest.raises(ValidationError):
        validate_condition({**PRESET, "threshold": bad_threshold})


def test_optional_fields_accepted():
    _, options = validate_condition(
        {**PRESET, "threshold": 0.1, "t_end": 800.0, "n_points": 200}
    )
    assert options["threshold"] == pytest.approx(0.1)
    assert options["t_end"] == pytest.approx(800.0)
    assert options["n_points"] == 200
