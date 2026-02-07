"""
Randomness Beacon implementation.
Provides unpredictable random values once f+1 parties request them.
"""

import asyncio
from field import Field


class RandomnessBeacon:
    """
    Randomness beacon that releases random values once f+1 parties request them.
    The beacon ensures unpredictability and fairness.
    """

    def __init__(self, n, f):
        self.n = n
        self.f = f
        self.threshold = f + 1

        # Counter for beacon values
        self.index = 0

        # Track requests for each index
        self.requests = {}  # index -> set of party ids

        # Store generated values
        self.values = {}  # index -> random value

        # Conditions for waiting parties
        self.conditions = {}  # index -> asyncio.Condition

        # Metrics
        self.total_invocations = 0

    async def request(self, party_id, index=None):
        """
        Party requests the beacon value at given index.
        If index is None, uses the next sequential index.
        Returns the beacon value once threshold requests are met.
        """
        if index is None:
            index = self.index
            self.index += 1

        # Initialize structures for this index
        if index not in self.requests:
            self.requests[index] = set()
            self.conditions[index] = asyncio.Condition()

        async with self.conditions[index]:
            # Add this party's request
            self.requests[index].add(party_id)

            # Check if we've reached threshold
            if len(self.requests[index]) >= self.threshold:
                if index not in self.values:
                    # Generate random value
                    self.values[index] = Field.random()
                    self.total_invocations += 1
                    # Notify all waiting parties
                    self.conditions[index].notify_all()

            # Wait for value to be generated
            while index not in self.values:
                await self.conditions[index].wait()

            return self.values[index]

    def get_invocation_count(self):
        """Return total number of beacon invocations."""
        return self.total_invocations

    def reset(self):
        """Reset the beacon for a new execution."""
        self.index = 0
        self.requests.clear()
        self.values.clear()
        self.conditions.clear()
        self.total_invocations = 0

