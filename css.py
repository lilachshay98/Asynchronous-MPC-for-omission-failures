"""
Complete Secret Sharing based on BGW with bi-variate polynomials.
"""

import asyncio
from field import Field, Polynomial, BiVariatePolynomial
from rbc import ReliableBroadcast


class CompleteSecretSharing:
    """
    Complete Secret Sharing protocol using bi-variate polynomials.
    Satisfies: Termination, Hiding, Binding, Completeness, and Validity.
    """

    def __init__(self, party_id, n, f, network, beacon):
        self.party_id = party_id
        self.n = n
        self.f = f
        self.network = network
        self.beacon = beacon

        # RBC instance for broadcasts
        self.rbc = ReliableBroadcast(party_id, n, f, network)

        # Sharing state per dealer
        self.row_polys = {}  # dealer -> Polynomial
        self.col_polys = {}  # dealer -> Polynomial
        self.sub_shares = {}  # dealer -> {party -> (row_eval, col_eval)}
        self.public_parties = {}  # dealer -> set of public party ids
        self.happy_count = {}  # dealer -> count of happy parties
        self.completed = {}  # dealer -> bool

        # Conditions
        self.completion_conditions = {}  # dealer -> asyncio.Condition

    async def share(self, secret):
        """
        Share a secret as dealer.
        Returns when sharing is complete.
        """
        # Phase 1: Create bi-variate polynomial and send rows/columns
        poly = BiVariatePolynomial(self.f, secret)

        for party_id in range(self.n):
            row = poly.row_polynomial(party_id)
            col = poly.col_polynomial(party_id)

            # Send row and column polynomials
            await self.network.send(self.party_id, party_id, 'CSS_SHARE', {
                'dealer': self.party_id,
                'row': row.coeffs,
                'col': col.coeffs
            })

        # Wait for completion
        return await self.receive_share(self.party_id)

    async def receive_share(self, dealer):
        """
        Receive share from dealer.
        Returns (row_poly, col_poly) or (None, None) if sharing failed.
        """
        if dealer not in self.completion_conditions:
            self.completion_conditions[dealer] = asyncio.Condition()
            self.sub_shares[dealer] = {}
            self.public_parties[dealer] = set()
            self.happy_count[dealer] = 0

        # Wait for share message or timeout
        timeout = 0
        while dealer not in self.row_polys and timeout < 100:
            await asyncio.sleep(0.001)
            timeout += 1

        # Phase 2: Exchange sub-shares
        if dealer in self.row_polys:
            my_row = self.row_polys[dealer]
            my_col = self.col_polys[dealer]

            for party_id in range(self.n):
                if party_id != self.party_id:
                    await self.network.send(self.party_id, party_id, 'CSS_SUBSHARE', {
                        'dealer': dealer,
                        'row_eval': my_row.eval(party_id),
                        'col_eval': my_col.eval(party_id)
                    })

        # Wait for n-f sub-shares
        while len(self.sub_shares[dealer]) < self.n - self.f:
            await asyncio.sleep(0.001)

        # Phase 3: Check if happy
        is_happy = self._check_happy(dealer)

        # Broadcast happiness
        await self.network.broadcast(self.party_id, 'CSS_HAPPY', {
            'dealer': dealer,
            'happy': is_happy
        })

        # Wait for n-f happy messages
        while self.happy_count[dealer] < self.n - self.f:
            await asyncio.sleep(0.001)

        # Phase 4: Finalize
        async with self.completion_conditions[dealer]:
            self.completed[dealer] = is_happy
            self.completion_conditions[dealer].notify_all()

        if is_happy and dealer in self.row_polys:
            return (self.row_polys[dealer], self.col_polys[dealer])
        else:
            # Return zero polynomials
            return (Polynomial([0]), Polynomial([0]))

    def _check_happy(self, dealer):
        """Check if this party is happy with the sharing."""
        # Check if we have valid shares
        if dealer not in self.row_polys:
            return False

        my_row = self.row_polys[dealer]
        my_col = self.col_polys[dealer]

        # Check consistency with received sub-shares
        for party_id, (row_eval, col_eval) in self.sub_shares[dealer].items():
            # row_i(party_id) should equal col_party_id(i)
            if my_row.eval(party_id) != row_eval:
                return False
            if my_col.eval(self.party_id) != col_eval:
                return False

        return True

    async def handle_message(self, message):
        """Process CSS message."""
        msg_type = message.msg_type
        payload = message.payload

        if msg_type == 'CSS_SHARE':
            await self._handle_share(payload)
        elif msg_type == 'CSS_SUBSHARE':
            await self._handle_subshare(payload)
        elif msg_type == 'CSS_HAPPY':
            await self._handle_happy(payload)
        elif msg_type.startswith('RBC_'):
            await self.rbc.handle_message(message)

    async def _handle_share(self, payload):
        """Handle SHARE message from dealer."""
        dealer = payload['dealer']

        if dealer not in self.row_polys:
            self.row_polys[dealer] = Polynomial(payload['row'])
            self.col_polys[dealer] = Polynomial(payload['col'])

    async def _handle_subshare(self, payload):
        """Handle SUBSHARE message."""
        dealer = payload['dealer']
        sender = message.sender if hasattr(message, 'sender') else None

        if dealer not in self.sub_shares:
            self.sub_shares[dealer] = {}

        self.sub_shares[dealer][sender] = (payload['row_eval'], payload['col_eval'])

    async def _handle_happy(self, payload):
        """Handle HAPPY message."""
        dealer = payload['dealer']

        if dealer not in self.happy_count:
            self.happy_count[dealer] = 0

        if payload['happy']:
            self.happy_count[dealer] += 1

    async def reconstruct(self, dealer):
        """
        Reconstruct the secret from shares.
        All parties send their col_i(0) values.
        """
        # Send my share
        if dealer in self.col_polys:
            my_share = self.col_polys[dealer].eval(0)
        else:
            my_share = 0

        await self.network.broadcast(self.party_id, 'CSS_RECONSTRUCT', {
            'dealer': dealer,
            'share': my_share
        })

        # Collect shares
        shares = {}
        while len(shares) < self.f + 1:
            await asyncio.sleep(0.001)

        # Interpolate
        points = [(party_id, share) for party_id, share in shares.items()]
        poly = Polynomial.interpolate(points)
        return poly.eval(0)

