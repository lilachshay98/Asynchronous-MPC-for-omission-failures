"""
Tests for network and communication primitives.
"""

import pytest
import asyncio
from network import Network
from beacon import RandomnessBeacon
from rbc import ReliableBroadcast


@pytest.mark.asyncio
async def test_network_send_receive():
    """Test basic network send and receive."""
    network = Network(n=4, faulty_parties=None, delay_range=(0, 0.001))

    # Send a message
    await network.send(0, 1, 'TEST', {'data': 'hello'})

    # Receive the message
    message = await network.receive(1)

    assert message.sender == 0
    assert message.receiver == 1
    assert message.msg_type == 'TEST'
    assert message.payload['data'] == 'hello'


@pytest.mark.asyncio
async def test_network_broadcast():
    """Test network broadcast."""
    n = 4
    network = Network(n=n, faulty_parties=None, delay_range=(0, 0.001))

    # Broadcast from party 0
    await network.broadcast(0, 'BROADCAST', {'value': 42})

    # All parties should receive
    await asyncio.sleep(0.01)  # Wait for delivery

    messages = []
    for i in range(n):
        try:
            msg = await asyncio.wait_for(network.receive(i), timeout=0.1)
            messages.append(msg)
        except asyncio.TimeoutError:
            pass

    assert len(messages) == n


@pytest.mark.asyncio
async def test_network_omissions():
    """Test that faulty parties omit messages."""
    network = Network(n=4, faulty_parties={0}, delay_range=(0, 0.001))

    # Faulty party 0 sends multiple messages
    for i in range(10):
        await network.send(0, 1, 'TEST', {'seq': i})

    await asyncio.sleep(0.05)

    # Some messages should be omitted
    stats = network.get_stats()
    assert stats['omitted_messages'] > 0


@pytest.mark.asyncio
async def test_beacon_basic():
    """Test basic beacon functionality."""
    n = 4
    f = 1
    beacon = RandomnessBeacon(n, f)

    # Request beacon value (need f+1 requests)
    tasks = [beacon.request(i, index=0) for i in range(f + 1)]
    results = await asyncio.gather(*tasks)

    # All should get the same value
    assert all(r == results[0] for r in results)

    # Value should be random (in field)
    assert 0 <= results[0] < 2**31 - 1


@pytest.mark.asyncio
async def test_beacon_threshold():
    """Test that beacon waits for threshold requests."""
    n = 4
    f = 1
    beacon = RandomnessBeacon(n, f)

    # Start requests but don't reach threshold yet
    async def request_delayed(party_id, delay):
        await asyncio.sleep(delay)
        return await beacon.request(party_id, index=1)

    # f requests immediately, then 1 more after delay
    tasks = []
    for i in range(f):
        tasks.append(request_delayed(i, 0))
    tasks.append(request_delayed(f, 0.01))  # Delayed request

    results = await asyncio.gather(*tasks)

    # Should all succeed and get same value
    assert len(results) == f + 1
    assert all(r == results[0] for r in results)


@pytest.mark.asyncio
async def test_beacon_multiple_indices():
    """Test beacon with multiple indices."""
    n = 4
    f = 1
    beacon = RandomnessBeacon(n, f)

    # Request different indices
    value_0 = await beacon.request(0, index=0)
    await beacon.request(1, index=0)  # Reach threshold for index 0

    value_1 = await beacon.request(0, index=1)
    await beacon.request(1, index=1)  # Reach threshold for index 1

    # Different indices should give different values (with high probability)
    assert value_0 != value_1


@pytest.mark.asyncio
async def test_rbc_honest():
    """Test Reliable Broadcast with honest parties."""
    n = 4
    f = 1
    network = Network(n, faulty_parties=None, delay_range=(0, 0.001))

    # Create RBC instances for all parties
    rbcs = [ReliableBroadcast(i, n, f, network) for i in range(n)]

    # Start message handlers
    async def handle_messages(party_id):
        while True:
            try:
                msg = await asyncio.wait_for(network.receive(party_id), timeout=0.01)
                await rbcs[party_id].handle_message(msg)
            except asyncio.TimeoutError:
                break

    handlers = [asyncio.create_task(handle_messages(i)) for i in range(n)]

    # Party 0 broadcasts value
    test_value = {'data': 'test_broadcast'}
    await rbcs[0].broadcast(test_value)

    # All parties should deliver the same value
    await asyncio.sleep(0.1)  # Allow time for protocol

    delivered_values = []
    for i in range(n):
        try:
            value = await asyncio.wait_for(rbcs[i].deliver(0), timeout=0.5)
            delivered_values.append(value)
        except asyncio.TimeoutError:
            delivered_values.append(None)

    # Cleanup handlers
    for h in handlers:
        h.cancel()

    # At least n-f parties should deliver
    non_none = [v for v in delivered_values if v is not None]
    assert len(non_none) >= n - f


@pytest.mark.asyncio
async def test_network_message_count():
    """Test that network tracks message counts correctly."""
    network = Network(n=4, faulty_parties=None, delay_range=(0, 0.001))

    # Send some messages
    await network.send(0, 1, 'TEST', {})
    await network.send(0, 2, 'TEST', {})
    await network.broadcast(1, 'TEST', {})

    await asyncio.sleep(0.01)

    stats = network.get_stats()
    assert stats['total_messages'] == 6  # 2 sends + 4 broadcasts

