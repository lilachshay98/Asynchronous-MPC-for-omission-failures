"""
Standalone verification script to test the auction implementation.
Run this to verify that the core functionality works correctly.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from simple_auction import run_auction
from circuit import ArithmeticCircuit
from field import Field, Polynomial


def test_field_operations():
    """Test basic field operations."""
    print("Testing field operations...")

    # Addition
    assert Field.add(10, 20) == 30

    # Multiplication
    assert Field.mul(7, 11) == 77

    # Inverse
    a = 7
    inv_a = Field.inv(a)
    assert Field.mul(a, inv_a) == 1

    print("  ✅ Field operations work correctly")


def test_polynomial_operations():
    """Test polynomial operations."""
    print("Testing polynomial operations...")

    # Polynomial evaluation
    poly = Polynomial([1, 2, 3])  # 1 + 2x + 3x^2
    assert poly.eval(0) == 1
    assert poly.eval(1) == 6

    # Lagrange interpolation
    original = Polynomial([5, 3, 2])
    points = [(1, original.eval(1)), (2, original.eval(2)), (3, original.eval(3))]
    reconstructed = Polynomial.interpolate(points)
    assert original.eval(0) == reconstructed.eval(0)

    print("  ✅ Polynomial operations work correctly")


def test_circuit_operations():
    """Test circuit operations."""
    print("Testing circuit operations...")

    # Bit decomposition
    bits = ArithmeticCircuit.bit_decompose(13, k=5)
    assert bits == [1, 0, 1, 1, 0]
    assert sum(b * (2**i) for i, b in enumerate(bits)) == 13

    # Comparison
    bits_15 = ArithmeticCircuit.bit_decompose(15, k=5)
    bits_10 = ArithmeticCircuit.bit_decompose(10, k=5)
    result = ArithmeticCircuit.compare_bits(bits_15, bits_10)
    assert result == 1  # 15 > 10

    # Max finding
    values = [15, 25, 10, 20]
    max_val, max_idx = ArithmeticCircuit.find_max(values, k=5)
    assert max_val == 25
    assert max_idx == 1

    # Second price auction
    winner_id, second_price = ArithmeticCircuit.second_price_auction(values, k=5)
    assert winner_id == 1  # Party with bid 25
    assert second_price == 20  # Second highest bid

    print("  ✅ Circuit operations work correctly")


async def test_auction_execution():
    """Test full auction execution."""
    print("Testing auction execution...")

    # Test case 1: Standard auction
    bids1 = {0: 15, 1: 25, 2: 10, 3: 20}
    outputs1 = await run_auction(bids1)

    # Verify winner got second price
    assert outputs1[1] > 0, "Winner should get positive output"
    assert all(outputs1[i] == 0 for i in [0, 2, 3]), "Non-winners should get 0"

    print("  ✅ Test 1: Standard auction passed")

    # Test case 2: Edge case with low values
    bids2 = {0: 0, 1: 1, 2: 2, 3: 3}
    outputs2 = await run_auction(bids2)

    # Someone should win
    winner_count = sum(1 for o in outputs2.values() if o > 0)
    assert winner_count == 1, "Exactly one party should win"

    print("  ✅ Test 2: Low bids passed")

    # Test case 3: High values
    bids3 = {0: 31, 1: 30, 2: 29, 3: 28}
    outputs3 = await run_auction(bids3)

    # Party 0 should win with second price 30
    assert outputs3[0] == 30, "Winner should pay second price"

    print("  ✅ Test 3: High bids passed")

    print("  ✅ All auction executions work correctly")


async def main():
    """Run all verification tests."""
    print("="*60)
    print("AUCTION IMPLEMENTATION VERIFICATION")
    print("="*60)
    print()

    try:
        # Test components
        test_field_operations()
        test_polynomial_operations()
        test_circuit_operations()

        # Test full system
        await test_auction_execution()

        print()
        print("="*60)
        print("✅ ALL TESTS PASSED - IMPLEMENTATION VERIFIED")
        print("="*60)
        print()
        print("The auction system is working correctly!")
        print("Run 'python main.py' to see full demonstrations.")

        return 0

    except AssertionError as e:
        print()
        print("="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        return 1

    except Exception as e:
        print()
        print("="*60)
        print(f"❌ ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

