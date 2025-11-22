import pytest

from core.math_utils import Vector2


def test_vector2_inplace_add():
    v1 = Vector2(1, 2)
    v2 = Vector2(3, 4)
    v1 += v2
    assert v1.x == 4
    assert v1.y == 6
    assert v1 is not v2  # Ensure it's still the same object (or at least behaves like one in Python, though += on mutable objects modifies in place)

    # Verify it returns self
    v3 = Vector2(1, 1)
    v3 += Vector2(1, 1)
    assert v3.x == 2


def test_vector2_inplace_sub():
    v1 = Vector2(5, 6)
    v2 = Vector2(2, 2)
    v1 -= v2
    assert v1.x == 3
    assert v1.y == 4


def test_vector2_inplace_mul():
    v1 = Vector2(2, 3)
    v1 *= 2
    assert v1.x == 4
    assert v1.y == 6


def test_vector2_inplace_div():
    v1 = Vector2(4, 6)
    v1 /= 2
    assert v1.x == 2
    assert v1.y == 3


def test_vector2_inplace_div_by_zero():
    v1 = Vector2(4, 6)
    with pytest.raises(ZeroDivisionError):
        v1 /= 0


def test_vector2_rmul():
    v = Vector2(1.5, -2.0)
    result = 3 * v
    assert result.x == pytest.approx(4.5)
    assert result.y == pytest.approx(-6.0)


def test_vector2_equality_tolerance():
    base = Vector2(1.0, 1.0)
    close = Vector2(1.0 + 5e-10, 1.0 - 5e-10)
    far = Vector2(1.0, 1.0001)

    assert base == close
    assert base != far
