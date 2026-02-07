"""
Tests for arithmetic circuit operations.
"""

import pytest
from circuit import ArithmeticCircuit


def test_bit_decomposition():
    """Test bit decomposition."""
    # Test value 13 = 1101 in binary = 1 + 4 + 8
    bits = ArithmeticCircuit.bit_decompose(13, k=5)
    assert bits == [1, 0, 1, 1, 0]  # LSB first

    # Reconstruct
    value = sum(b * (2 ** i) for i, b in enumerate(bits))
    assert value == 13

    # Test value 0
    bits = ArithmeticCircuit.bit_decompose(0, k=5)
    assert bits == [0, 0, 0, 0, 0]

    # Test value 31 (max for 5 bits)
    bits = ArithmeticCircuit.bit_decompose(31, k=5)
    assert bits == [1, 1, 1, 1, 1]


def test_compare_bits():
    """Test bit comparison."""
    # 15 > 10
    bits_15 = ArithmeticCircuit.bit_decompose(15, k=5)
    bits_10 = ArithmeticCircuit.bit_decompose(10, k=5)
    result = ArithmeticCircuit.compare_bits(bits_15, bits_10)
    assert result == 1  # 15 > 10

    # 10 > 15 should be 0
    result = ArithmeticCircuit.compare_bits(bits_10, bits_15)
    assert result == 0  # 10 < 15

    # Equal values
    result = ArithmeticCircuit.compare_bits(bits_15, bits_15)
    assert result == 0  # 15 == 15, so not greater


def test_max_two():
    """Test max of two values."""
    a = 20
    b = 15
    a_bits = ArithmeticCircuit.bit_decompose(a, k=5)
    b_bits = ArithmeticCircuit.bit_decompose(b, k=5)

    max_val = ArithmeticCircuit.max_two(a, b, a_bits, b_bits)
    assert max_val == 20

    # Reverse
    max_val = ArithmeticCircuit.max_two(b, a, b_bits, a_bits)
    assert max_val == 20


def test_find_max():
    """Test finding maximum value."""
    values = [15, 25, 10, 20]
    max_val, max_idx = ArithmeticCircuit.find_max(values, k=5)

    assert max_val == 25
    assert max_idx == 1

    # Single value
    values = [7]
    max_val, max_idx = ArithmeticCircuit.find_max(values, k=5)
    assert max_val == 7
    assert max_idx == 0

    # All same (first one wins)
    values = [10, 10, 10]
    max_val, max_idx = ArithmeticCircuit.find_max(values, k=5)
    assert max_val == 10


def test_find_second_max():
    """Test finding second maximum."""
    values = [15, 25, 10, 20]
    second_max = ArithmeticCircuit.find_second_max(values, winner_idx=1, k=5)

    assert second_max == 20  # Second highest after masking 25


def test_second_price_auction():
    """Test complete second-price auction."""
    bids = [15, 25, 10, 20]
    winner_id, second_price = ArithmeticCircuit.second_price_auction(bids, k=5)

    assert winner_id == 1  # Party 1 has bid 25
    assert second_price == 20  # Second highest bid

    # Test with different bids
    bids = [5, 10, 3, 8]
    winner_id, second_price = ArithmeticCircuit.second_price_auction(bids, k=5)

    assert winner_id == 1  # Party 1 has bid 10
    assert second_price == 8  # Second highest bid

    # Edge case: two bids
    bids = [5, 10]
    winner_id, second_price = ArithmeticCircuit.second_price_auction(bids, k=5)

    assert winner_id == 1
    assert second_price == 5


def test_count_operations():
    """Test operation counting."""
    n = 4
    k = 5

    additions, multiplications = ArithmeticCircuit.count_operations(n, k)

    # Should be O(nk)
    assert additions > 0
    assert multiplications > 0
    assert additions == 2 * n * k
    assert multiplications == 2 * n * k

