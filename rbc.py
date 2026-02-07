"""
Bracha's Reliable Broadcast (RBC) protocol.
Ensures totality: if any honest party delivers, all honest parties deliver.
"""

import asyncio
from collections import defaultdict


class ReliableBroadcast:
    """
    Bracha's Reliable Broadcast protocol.
    Guarantees that if one honest party delivers a value, all honest parties deliver it.
    """

    def __init__(self, party_id, n, f, network):
        self.party_id = party_id
        self.n = n
        self.f = f
        self.network = network

        # Thresholds
        self.echo_threshold = (n + f + 1 + 1) // 2  # ceil((n+f+1)/2)
        self.ready_threshold = f + 1
        self.deliver_threshold = 2 * f + 1

        # State per sender
        self.val_received = {}  # sender -> value
        self.echo_count = defaultdict(lambda: defaultdict(int))  # sender -> value -> count
        self.ready_count = defaultdict(lambda: defaultdict(int))  # sender -> value -> count
        self.delivered = {}  # sender -> value

        # Flags
        self.echo_sent = {}  # sender -> bool
        self.ready_sent = {}  # sender -> value or None

        # Conditions for waiting
        self.deliver_conditions = {}  # sender -> asyncio.Condition

    async def broadcast(self, value):
        """Broadcast a value as the sender."""
        # Send VAL to all parties
        await self.network.broadcast(self.party_id, 'RBC_VAL', {
            'sender': self.party_id,
            'value': value
        })

    async def deliver(self, sender):
        """Wait for and return the delivered value from sender."""
        if sender not in self.deliver_conditions:
            self.deliver_conditions[sender] = asyncio.Condition()

        async with self.deliver_conditions[sender]:
            while sender not in self.delivered:
                await self.deliver_conditions[sender].wait()
            return self.delivered[sender]

    async def handle_message(self, message):
        """Process an RBC message."""
        msg_type = message.msg_type
        payload = message.payload

        if msg_type == 'RBC_VAL':
            await self._handle_val(payload)
        elif msg_type == 'RBC_ECHO':
            await self._handle_echo(payload)
        elif msg_type == 'RBC_READY':
            await self._handle_ready(payload)

    async def _handle_val(self, payload):
        """Handle VAL message."""
        sender = payload['sender']
        value = payload['value']

        # Only accept first VAL from sender
        if sender in self.val_received:
            return

        self.val_received[sender] = value

        # Send ECHO
        if sender not in self.echo_sent:
            self.echo_sent[sender] = True
            await self.network.broadcast(self.party_id, 'RBC_ECHO', {
                'sender': sender,
                'value': value
            })

    async def _handle_echo(self, payload):
        """Handle ECHO message."""
        sender = payload['sender']
        value = payload['value']

        self.echo_count[sender][value] += 1

        # Check ECHO threshold
        if (self.echo_count[sender][value] >= self.echo_threshold and
            self.ready_sent.get(sender) is None):
            self.ready_sent[sender] = value
            await self.network.broadcast(self.party_id, 'RBC_READY', {
                'sender': sender,
                'value': value
            })

    async def _handle_ready(self, payload):
        """Handle READY message."""
        sender = payload['sender']
        value = payload['value']

        self.ready_count[sender][value] += 1

        # Amplification: if f+1 READY, send READY if not already sent
        if (self.ready_count[sender][value] >= self.ready_threshold and
            self.ready_sent.get(sender) is None):
            self.ready_sent[sender] = value
            await self.network.broadcast(self.party_id, 'RBC_READY', {
                'sender': sender,
                'value': value
            })

        # Delivery: if 2f+1 READY, deliver
        if (self.ready_count[sender][value] >= self.deliver_threshold and
            sender not in self.delivered):
            self.delivered[sender] = value

            # Notify waiting tasks
            if sender in self.deliver_conditions:
                async with self.deliver_conditions[sender]:
                    self.deliver_conditions[sender].notify_all()

