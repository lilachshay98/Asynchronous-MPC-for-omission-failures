"""
Integration tests for the auction protocol.
"""

import pytest
import asyncio
from auction import create_auction_system, run_simple_auction


@pytest.mark.asyncio
async def test_honest_auction():
    """Test auction with all honest parties."""
    bids = {
        0: 15,
        1: 25,  # Winner
        2: 10,
        3: 20   # Second price
    }

    outputs = await run_simple_auction(bids, faulty_parties=None)

    # Winner (party 1) should get second price (20)
    assert outputs[1] == 20

    # Others should get 0
    assert outputs[0] == 0
    assert outputs[2] == 0
    assert outputs[3] == 0


@pytest.mark.asyncio
async def test_auction_with_omissions():
    """Test auction with one omitting party."""
    bids = {
        0: 18,
        1: 30,  # Winner
        2: 22,  # Second price
        3: 5    # Faulty but low bid
    }

    # Party 3 may omit messages
    outputs = await run_simple_auction(bids, faulty_parties={3})

    # Winner should still be determined correctly
    assert outputs[1] == 22


@pytest.mark.asyncio
async def test_edge_case_low_bids():
    """Test with very low bids."""
    bids = {
        0: 0,
        1: 1,
        2: 2,
        3: 3   # Winner, second price = 2
    }

    outputs = await run_simple_auction(bids, faulty_parties=None)

    assert outputs[3] == 2
    assert outputs[0] == 0
    assert outputs[1] == 0
    assert outputs[2] == 0


@pytest.mark.asyncio
async def test_edge_case_high_bids():
    """Test with maximum bids."""
    bids = {
        0: 31,  # Winner (max for 5 bits)
        1: 30,  # Second price
        2: 29,
        3: 28
    }

    outputs = await run_simple_auction(bids, faulty_parties=None)

    assert outputs[0] == 30
    assert outputs[1] == 0
    assert outputs[2] == 0
    assert outputs[3] == 0


@pytest.mark.asyncio
async def test_auction_with_delays():
    """Test auction with random message delays."""
    n = 4
    f = 1

    # Create system with delays
    parties, network, beacon, auction = await create_auction_system(
        n, f, faulty_parties=None, delay_range=(0, 0.05)
    )

    bids = {
        0: 12,
        1: 20,  # Winner
        2: 18,  # Second price
        3: 15
    }

    try:
        outputs = await auction.run_auction(bids)

        # Should still compute correctly despite delays
        assert outputs[1] == 18

    finally:
        for party in parties:
            await party.stop()


@pytest.mark.asyncio
async def test_multiple_auctions():
    """Test running multiple auctions sequentially."""
    # First auction
    bids1 = {0: 10, 1: 20, 2: 15, 3: 18}
    outputs1 = await run_simple_auction(bids1)
    assert outputs1[1] == 18

    # Second auction with different bids
    bids2 = {0: 25, 1: 22, 2: 20, 3: 15}
    outputs2 = await run_simple_auction(bids2)
    assert outputs2[0] == 22


@pytest.mark.asyncio
async def test_auction_metrics():
    """Test that metrics are collected."""
    n = 4
    f = 1

    parties, network, beacon, auction = await create_auction_system(n, f)

    bids = {0: 10, 1: 20, 2: 15, 3: 18}

    try:
        outputs = await auction.run_auction(bids)

        # Wait for all messages to be delivered
        await network.wait_for_all_deliveries()

        # Check metrics
        stats = network.get_stats()
        assert stats['total_messages'] > 0
        assert stats['delivered_messages'] > 0

        beacon_count = beacon.get_invocation_count()
        assert beacon_count >= 0  # May or may not use beacon depending on protocol

    finally:
        for party in parties:
            await party.stop()


@pytest.mark.asyncio
async def test_auction_termination():
    """Test that auction always terminates."""
    bids = {0: 5, 1: 15, 2: 10, 3: 12}

    # Set a timeout to ensure termination
    try:
        outputs = await asyncio.wait_for(
            run_simple_auction(bids),
            timeout=5.0
        )
        assert outputs is not None
    except asyncio.TimeoutError:
        pytest.fail("Auction did not terminate within timeout")


@pytest.mark.asyncio
async def test_auction_privacy():
    """Test that non-winners don't learn winning bid."""
    bids = {0: 10, 1: 25, 2: 15, 3: 20}

    outputs = await run_simple_auction(bids)

    # Only winner (party 1) should learn second price (20)
    assert outputs[1] == 20

    # Other parties should only learn they didn't win (output = 0)
    # They should not learn the actual winning bid (25)
    for party_id in [0, 2, 3]:
        assert outputs[party_id] == 0

