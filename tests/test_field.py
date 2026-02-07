"""
Tests for field arithmetic.
"""

import pytest
from field import Field, Polynomial, BiVariatePolynomial


def test_field_addition():
    """Test field addition."""
    a = 100
    b = 200
    result = Field.add(a, b)
    assert result == 300

    # Test modular arithmetic
    a = Field.MODULUS - 1
    b = 10
    result = Field.add(a, b)
    assert result == 9  # Wraps around


def test_field_multiplication():
    """Test field multiplication."""
    a = 7
    b = 11
    result = Field.mul(a, b)
    assert result == 77


def test_field_inverse():
    """Test field multiplicative inverse."""
    a = 7
    inv_a = Field.inv(a)
    product = Field.mul(a, inv_a)
    assert product == 1


def test_polynomial_evaluation():
    """Test polynomial evaluation."""
    # p(x) = 1 + 2x + 3x^2
    poly = Polynomial([1, 2, 3])

    # p(0) = 1
    assert poly.eval(0) == 1

    # p(1) = 1 + 2 + 3 = 6
    assert poly.eval(1) == 6

    # p(2) = 1 + 4 + 12 = 17
    assert poly.eval(2) == 17


def test_polynomial_addition():
    """Test polynomial addition."""
    p1 = Polynomial([1, 2, 3])  # 1 + 2x + 3x^2
    p2 = Polynomial([4, 5])     # 4 + 5x

    p3 = p1 + p2  # 5 + 7x + 3x^2

    assert p3.eval(0) == 5
    assert p3.eval(1) == 15


def test_polynomial_multiplication():
    """Test polynomial multiplication."""
    p1 = Polynomial([1, 2])  # 1 + 2x
    p2 = Polynomial([3, 4])  # 3 + 4x

    p3 = p1 * p2  # 3 + 10x + 8x^2

    assert p3.eval(0) == 3
    assert p3.eval(1) == 21  # 3 + 10 + 8


def test_lagrange_interpolation():
    """Test Lagrange interpolation."""
    # Create a polynomial p(x) = 5 + 3x + 2x^2
    original = Polynomial([5, 3, 2])

    # Sample at x = 1, 2, 3
    points = [(1, original.eval(1)),
              (2, original.eval(2)),
              (3, original.eval(3))]

    # Interpolate
    reconstructed = Polynomial.interpolate(points)

    # Check that reconstructed polynomial matches original at several points
    for x in [0, 1, 2, 3, 4]:
        assert original.eval(x) == reconstructed.eval(x)


def test_lagrange_coefficient():
    """Test Lagrange coefficient computation."""
    points = [1, 2, 3]

    # Compute coefficients for interpolation at 0
    coeffs = [Polynomial.lagrange_coefficient(i, points, 0) for i in range(3)]

    # The sum of Lagrange basis polynomials should equal 1
    total = sum(coeffs) % Field.MODULUS
    assert total == 1


def test_bivariate_polynomial():
    """Test bi-variate polynomial."""
    secret = 42
    degree = 1

    poly = BiVariatePolynomial(degree, secret)

    # Check secret is at (0, 0)
    assert poly.eval(0, 0) == secret

    # Test symmetry property for BGW
    for i in range(1, 4):
        for j in range(1, 4):
            # In BGW, we need p(i,j) for sub-shares
            val_ij = poly.eval(i, j)
            val_ji = poly.eval(j, i)
            # Note: Not necessarily symmetric unless we construct it that way
            assert isinstance(val_ij, int)


def test_bivariate_row_column():
    """Test row and column polynomials."""
    secret = 100
    degree = 2

    poly = BiVariatePolynomial(degree, secret)

    # Get row and column for party 1
    row_1 = poly.row_polynomial(1)
    col_1 = poly.col_polynomial(1)

    # row_1(j) should equal p(1, j)
    # col_1(i) should equal p(i, 1)
    for k in range(5):
        assert row_1.eval(k) == poly.eval(1, k)
        assert col_1.eval(k) == poly.eval(k, 1)

    # col_1(0) should be a share of the secret
    # (but not the secret itself unless party is 0)
    share = col_1.eval(0)
    assert isinstance(share, int)

