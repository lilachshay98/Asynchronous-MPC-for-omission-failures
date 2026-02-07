"""
Main entry point for the auction system.
"""

import asyncio
from simple_auction import run_auction


async def main():
    """Run example auctions."""

    print("=" * 60)
    print("ASYNCHRONOUS MPC AUCTION SYSTEM")
    print("=" * 60)
    print(f"System: n=4 parties, f=1 fault tolerance")
    print(f"Bids: 5-bit integers (range [0, 32))")
    print("=" * 60)

    # Test 1: Honest execution
    print("\n\n" + "=" * 60)
    print("TEST 1: Honest Execution (all parties participate)")
    print("=" * 60)

    bids1 = {
        0: 15,  # Party 0 bids 15
        1: 25,  # Party 1 bids 25 (winner)
        2: 10,  # Party 2 bids 10
        3: 20   # Party 3 bids 20 (second highest)
    }

    outputs1 = await run_auction(bids1)

    print("\nExpected: Party 1 wins and pays 20 (second price)")
    print(f"Result: Party 1 output = {outputs1[1]} (expected 20)")

    # Test 2: One faulty party (simulated - same result)
    print("\n\n" + "=" * 60)
    print("TEST 2: Different Bids")
    print("=" * 60)

    bids2 = {
        0: 18,
        1: 30,
        2: 22,
        3: 5
    }

    outputs2 = await run_auction(bids2)

    # Test 3: Edge case - minimum bids
    print("\n\n" + "=" * 60)
    print("TEST 3: Edge Case - Low Bids")
    print("=" * 60)

    bids3 = {
        0: 0,
        1: 1,
        2: 2,
        3: 3
    }

    outputs3 = await run_auction(bids3)

    print("\nExpected: Party 3 wins and pays 2")

    # Test 4: Edge case - high bids
    print("\n\n" + "=" * 60)
    print("TEST 4: Edge Case - High Bids")
    print("=" * 60)

    bids4 = {
        0: 31,
        1: 30,
        2: 29,
        3: 28
    }

    outputs4 = await run_auction(bids4)

    print("\nExpected: Party 0 wins and pays 30")

    print("\n\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

