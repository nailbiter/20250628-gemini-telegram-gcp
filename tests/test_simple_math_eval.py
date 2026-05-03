import pytest
from common.simple_math_eval import simple_math_eval


@pytest.mark.parametrize("expr,expected", [
    ("15", 15),
    ("0", 0),
    ("14.7", 14.7),
    ("3.14", 3.14),
    ("5+5", 10),
    ("85+14.7", 85 + 14.7),
    ("1+2+3", 6),
    ("100-14.7", 100 - 14.7),
    ("3*4", 12),
    ("2.5*4", 10.0),
    ("10/4", 2.5),
    ("2+3*4", 14),
    ("10-2*3", 4),
])
def test_simple_math_eval(expr, expected):
    assert simple_math_eval(expr) == pytest.approx(expected)
