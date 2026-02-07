"""
Asynchronous network simulator with message delays and omissions.
"""

import asyncio
import random
from collections import defaultdict


class Message:
    """Network message."""

    def __init__(self, sender, receiver, msg_type, payload):
        self.sender = sender
        self.receiver = receiver
        self.msg_type = msg_type
        self.payload = payload

    def __repr__(self):
        return f"Message({self.sender}->{self.receiver}, {self.msg_type})"


class Network:
    """
    Asynchronous network simulator.
    Supports message delays and omissions from faulty parties.
    """

    def __init__(self, n, faulty_parties=None, delay_range=(0, 0.01)):
        """
        Args:
            n: Number of parties
            faulty_parties: Set of party IDs that may omit messages
            delay_range: (min_delay, max_delay) for message delivery
        """
        self.n = n
        self.faulty_parties = faulty_parties or set()
        self.delay_range = delay_range

        # Message queues for each party
        self.queues = {i: asyncio.Queue() for i in range(n)}

        # Metrics
        self.total_messages = 0
        self.delivered_messages = 0
        self.omitted_messages = 0

        # Message delivery tasks
        self.delivery_tasks = []

    async def send(self, sender, receiver, msg_type, payload):
        """Send a message from sender to receiver."""
        # Check if sender is faulty and should omit
        if sender in self.faulty_parties:
            # With some probability, omit the message
            if random.random() < 0.3:  # 30% omission rate for faulty parties
                self.omitted_messages += 1
                return

        self.total_messages += 1

        # Simulate network delay
        delay = random.uniform(*self.delay_range)

        # Create and deliver message after delay
        message = Message(sender, receiver, msg_type, payload)
        task = asyncio.create_task(self._deliver_with_delay(message, delay))
        self.delivery_tasks.append(task)

    async def _deliver_with_delay(self, message, delay):
        """Deliver a message after the specified delay."""
        await asyncio.sleep(delay)
        await self.queues[message.receiver].put(message)
        self.delivered_messages += 1

    async def broadcast(self, sender, msg_type, payload):
        """Broadcast a message to all parties."""
        for receiver in range(self.n):
            await self.send(sender, receiver, msg_type, payload)

    async def receive(self, party_id):
        """Receive next message for a party."""
        return await self.queues[party_id].get()

    def get_message_count(self):
        """Return total number of messages sent."""
        return self.total_messages

    def get_stats(self):
        """Return network statistics."""
        return {
            'total_messages': self.total_messages,
            'delivered_messages': self.delivered_messages,
            'omitted_messages': self.omitted_messages
        }

    async def wait_for_all_deliveries(self):
        """Wait for all pending message deliveries."""
        if self.delivery_tasks:
            await asyncio.gather(*self.delivery_tasks, return_exceptions=True)
            self.delivery_tasks.clear()

