"""
Asynchronous Binary Agreement (ABA) protocol.
Uses randomness beacon as common coin for termination.
"""

import asyncio
from collections import defaultdict


class BinaryAgreement:
    """
    Asynchronous Binary Agreement using randomness beacon.
    Guarantees agreement on a binary value with randomized termination.
    """

    def __init__(self, party_id, n, f, network, beacon, instance_id):
        self.party_id = party_id
        self.n = n
        self.f = f
        self.network = network
        self.beacon = beacon
        self.instance_id = instance_id

        # Current round and estimate
        self.round = 0
        self.estimate = None
        self.decided = False
        self.decision = None

        # Message counts per round
        self.est_count = defaultdict(lambda: defaultdict(int))  # round -> value -> count
        self.aux_count = defaultdict(lambda: defaultdict(int))  # round -> value -> count

        # Sent flags
        self.est_sent = defaultdict(bool)  # round -> bool
        self.aux_sent = defaultdict(bool)  # round -> bool

        # Conditions
        self.decision_condition = asyncio.Condition()

    async def propose(self, value):
        """Propose a binary value (0 or 1)."""
        assert value in [0, 1], "Value must be binary"
        self.estimate = value

        # Start the protocol
        asyncio.create_task(self._run_round())

        # Wait for decision
        async with self.decision_condition:
            while not self.decided:
                await self.decision_condition.wait()
            return self.decision

    async def _run_round(self):
        """Run one round of the ABA protocol."""
        while not self.decided:
            r = self.round

            # Send EST message
            if not self.est_sent[r]:
                self.est_sent[r] = True
                await self.network.broadcast(self.party_id, 'ABA_EST', {
                    'instance': self.instance_id,
                    'round': r,
                    'value': self.estimate
                })

            # Wait for n-f EST messages
            while sum(self.est_count[r].values()) < self.n - self.f:
                await asyncio.sleep(0.001)

            # Determine AUX value
            if self.est_count[r][self.estimate] >= (self.n - self.f):
                aux_value = self.estimate
            else:
                # Check if there's a clear majority
                if self.est_count[r][0] > self.est_count[r][1]:
                    aux_value = 0
                elif self.est_count[r][1] > self.est_count[r][0]:
                    aux_value = 1
                else:
                    aux_value = None  # No clear majority

            # Send AUX message
            if not self.aux_sent[r]:
                self.aux_sent[r] = True
                await self.network.broadcast(self.party_id, 'ABA_AUX', {
                    'instance': self.instance_id,
                    'round': r,
                    'value': aux_value
                })

            # Wait for n-f AUX messages
            while sum(self.aux_count[r].values()) < self.n - self.f:
                await asyncio.sleep(0.001)

            # Check if we can decide
            values_with_nf = [v for v in [0, 1] if self.aux_count[r][v] >= self.n - self.f]

            if values_with_nf:
                # At least one value has n-f support
                if len(values_with_nf) == 1:
                    # Only one value, can decide
                    self.decision = values_with_nf[0]
                    self.decided = True
                    async with self.decision_condition:
                        self.decision_condition.notify_all()
                    return
                else:
                    # Both values have support, use coin
                    coin = await self.beacon.request(self.party_id)
                    coin_bit = coin % 2
                    self.estimate = coin_bit
            else:
                # No value has n-f support, use coin
                coin = await self.beacon.request(self.party_id)
                coin_bit = coin % 2
                self.estimate = coin_bit

            # Move to next round
            self.round += 1

    async def handle_message(self, message):
        """Process an ABA message."""
        msg_type = message.msg_type
        payload = message.payload

        # Check if message is for this instance
        if payload.get('instance') != self.instance_id:
            return

        if msg_type == 'ABA_EST':
            await self._handle_est(payload)
        elif msg_type == 'ABA_AUX':
            await self._handle_aux(payload)

    async def _handle_est(self, payload):
        """Handle EST message."""
        r = payload['round']
        value = payload['value']

        if value in [0, 1]:
            self.est_count[r][value] += 1

    async def _handle_aux(self, payload):
        """Handle AUX message."""
        r = payload['round']
        value = payload['value']

        if value in [0, 1, None]:
            self.aux_count[r][value] += 1

