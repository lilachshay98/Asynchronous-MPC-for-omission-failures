"""
MPC Party implementation.
Handles message routing and protocol execution.
"""

import asyncio
from css import CompleteSecretSharing
from acs import AgreementOnCommonSet
from rbc import ReliableBroadcast
from field import Field, Polynomial


class MPCParty:
    """
    MPC Party that participates in the auction protocol.
    """

    def __init__(self, party_id, n, f, network, beacon):
        self.party_id = party_id
        self.n = n
        self.f = f
        self.network = network
        self.beacon = beacon

        # Protocol instances
        self.css = CompleteSecretSharing(party_id, n, f, network, beacon)
        self.acs = AgreementOnCommonSet(party_id, n, f, network, beacon)

        # Shares storage
        self.my_shares = {}  # secret_id -> (row_poly, col_poly)
        self.shared_values = {}  # secret_id -> share value

        # Message handler running
        self.running = False
        self.handler_task = None

    async def start(self):
        """Start the party's message handler."""
        self.running = True
        self.handler_task = asyncio.create_task(self._message_handler())

    async def stop(self):
        """Stop the party."""
        self.running = False
        if self.handler_task:
            self.handler_task.cancel()
            try:
                await self.handler_task
            except asyncio.CancelledError:
                pass

    async def _message_handler(self):
        """Handle incoming messages."""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.network.receive(self.party_id),
                    timeout=0.01
                )

                # Route message to appropriate handler
                if message.msg_type.startswith('CSS_'):
                    await self.css.handle_message(message)
                elif message.msg_type.startswith('RBC_'):
                    await self.css.rbc.handle_message(message)
                    await self.acs.rbc.handle_message(message)
                elif message.msg_type.startswith('ABA_'):
                    await self.acs.handle_message(message)
                elif message.msg_type == 'SHARE_VALUE':
                    await self._handle_share_value(message)
                elif message.msg_type == 'RECONSTRUCT_VALUE':
                    await self._handle_reconstruct_value(message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Silently ignore errors in async environment
                pass

    async def share_value(self, value, secret_id):
        """
        Share a value using Complete Secret Sharing.
        Returns when sharing is complete.
        """
        # Use CSS to share
        row_poly, col_poly = await self.css.share(value)
        self.my_shares[secret_id] = (row_poly, col_poly)

        # Store my share value (col_poly(0))
        if col_poly:
            self.shared_values[secret_id] = col_poly.eval(0)
        else:
            self.shared_values[secret_id] = 0

        return self.shared_values[secret_id]

    async def receive_share(self, dealer, secret_id):
        """
        Receive a share from a dealer.
        """
        row_poly, col_poly = await self.css.receive_share(dealer)
        self.my_shares[secret_id] = (row_poly, col_poly)

        # Store my share value
        if col_poly:
            self.shared_values[secret_id] = col_poly.eval(0)
        else:
            self.shared_values[secret_id] = 0

        return self.shared_values[secret_id]

    async def local_add(self, secret_id1, secret_id2, result_id):
        """
        Locally add two shared values.
        """
        share1 = self.shared_values.get(secret_id1, 0)
        share2 = self.shared_values.get(secret_id2, 0)
        result = Field.add(share1, share2)
        self.shared_values[result_id] = result
        return result

    async def local_multiply_constant(self, secret_id, constant, result_id):
        """
        Multiply a shared value by a public constant.
        """
        share = self.shared_values.get(secret_id, 0)
        result = Field.mul(share, constant)
        self.shared_values[result_id] = result
        return result

    async def multiply_shared(self, secret_id1, secret_id2, result_id):
        """
        Multiply two shared values using BGW multiplication.
        This is a simplified version for the auction.
        """
        # Initialize storage for this multiplication
        if not hasattr(self, '_mult_shares'):
            self._mult_shares = {}
        self._mult_shares[result_id] = {}

        # Phase 1: Local multiplication (creates degree 2f sharing)
        share1 = self.shared_values.get(secret_id1, 0)
        share2 = self.shared_values.get(secret_id2, 0)
        d_i = Field.mul(share1, share2)

        # Store own share
        self._mult_shares[result_id][self.party_id] = d_i

        # Broadcast d_i
        await self.network.broadcast(self.party_id, 'SHARE_VALUE', {
            'secret_id': result_id,
            'share': d_i,
            'party': self.party_id
        })

        # Phase 2: Wait for n-f shares
        # At least n-f honest parties will send their shares, and messages will eventually arrive
        while len(self._mult_shares[result_id]) < self.n - self.f:
            await asyncio.sleep(0.001)  # Yield to message handler

        # Degree reduction: take first f+1 shares and interpolate at my point
        collected_shares = self._mult_shares[result_id]
        parties = sorted(collected_shares.keys())[: self.f + 1]

        # Compute Lagrange coefficient for interpolation at my party_id
        my_new_share = 0
        for p in parties:
            coeff = Polynomial.lagrange_coefficient(
                parties.index(p),
                parties,
                eval_point=self.party_id
            )
            my_new_share = Field.add(my_new_share,
                                    Field.mul(coeff, collected_shares[p]))

        self.shared_values[result_id] = my_new_share
        return my_new_share


    async def reconstruct(self, secret_id):
        """
        Reconstruct a secret value.
        All parties send their shares and interpolate.
        """
        # Initialize storage for reconstruction
        if not hasattr(self, '_reconstruct_shares'):
            self._reconstruct_shares = {}
        self._reconstruct_shares[secret_id] = {}

        # Broadcast my share
        my_share = self.shared_values.get(secret_id, 0)

        # Store own share
        self._reconstruct_shares[secret_id][self.party_id] = my_share

        await self.network.broadcast(self.party_id, 'RECONSTRUCT_VALUE', {
            'secret_id': secret_id,
            'share': my_share,
            'party': self.party_id
        })

        # Wait for f+1 shares
        # At least f+1 honest parties will send their shares
        while len(self._reconstruct_shares[secret_id]) < self.f + 1:
            await asyncio.sleep(0.001)  # Yield to message handler

        # Interpolate
        shares = self._reconstruct_shares[secret_id]
        parties = sorted(shares.keys())[: self.f + 1]
        points = [(p, shares[p]) for p in parties]
        poly = Polynomial.interpolate(points)
        return poly.eval(0)


    async def _handle_share_value(self, message):
        """Handle shared value from multiplication."""
        payload = message.payload
        secret_id = payload['secret_id']
        share = payload['share']
        party = payload['party']

        # Store in temporary collection (would be better structured)
        if not hasattr(self, '_mult_shares'):
            self._mult_shares = {}
        if secret_id not in self._mult_shares:
            self._mult_shares[secret_id] = {}

        self._mult_shares[secret_id][party] = share

    async def _handle_reconstruct_value(self, message):
        """Handle reconstruction share."""
        payload = message.payload
        secret_id = payload['secret_id']
        share = payload['share']
        party = payload['party']

        # Store in temporary collection
        if not hasattr(self, '_reconstruct_shares'):
            self._reconstruct_shares = {}
        if secret_id not in self._reconstruct_shares:
            self._reconstruct_shares[secret_id] = {}

        self._reconstruct_shares[secret_id][party] = share

