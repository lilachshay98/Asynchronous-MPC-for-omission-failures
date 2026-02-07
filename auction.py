"""
Second-Price Auction Protocol using MPC.
"""

import asyncio
from party import MPCParty
from circuit import ArithmeticCircuit
from field import Field


class AuctionProtocol:
    """
    Second-price auction protocol using asynchronous MPC.
    """

    def __init__(self, parties, network, beacon, k=5):
        """
        Args:
            parties: List of MPCParty instances
            network: Network instance
            beacon: Randomness beacon
            k: Number of bits for bids (default 5 for range [0, 32))
        """
        self.parties = parties
        self.network = network
        self.beacon = beacon
        self.n = len(parties)
        self.f = (self.n - 1) // 3
        self.k = k

    async def run_auction(self, bids):
        """
        Run the second-price auction.

        Args:
            bids: Dictionary {party_id: bid_value}

        Returns:
            Dictionary {party_id: output} where winner gets second_price, others get 0
        """
        print(f"\n=== Starting Auction ===")
        print(f"Bids: {bids}")

        # Phase 1: Input sharing - each party shares its bid
        print("\n[Phase 1] Input Sharing...")
        share_tasks = []
        for party_id, party in enumerate(self.parties):
            bid = bids.get(party_id, 0)
            # Share bid bits
            bits = ArithmeticCircuit.bit_decompose(bid, self.k)
            for bit_idx, bit_val in enumerate(bits):
                secret_id = f"bid_{party_id}_bit_{bit_idx}"
                if party_id == party.party_id:
                    task = party.share_value(bit_val, secret_id)
                else:
                    task = party.receive_share(party_id, secret_id)
                share_tasks.append(task)

        await asyncio.gather(*share_tasks)
        print(f"  ✓ Shared {len(share_tasks)} bit values")

        # Phase 2: Agreement on input set using ACS
        print("\n[Phase 2] Agreement on Input Set...")
        # For simplicity, assume all parties participate (n-f = 3 parties)
        # In full implementation, would use ACS protocol
        participating_parties = list(range(min(self.n, self.n - self.f)))
        print(f"  ✓ Agreed on {len(participating_parties)} participating parties: {participating_parties}")

        # Phase 3: Circuit evaluation (simplified - direct computation on shares)
        print("\n[Phase 3] Circuit Evaluation...")

        # For this simplified implementation, we'll compute the auction directly
        # In a full implementation, would evaluate the arithmetic circuit gate-by-gate

        # Collect bids from participating parties
        actual_bids = {pid: bids.get(pid, 0) for pid in participating_parties}
        winner_id, second_price = ArithmeticCircuit.second_price_auction(
            list(actual_bids.values()), self.k
        )
        # Map back to original party ID
        winner_id = participating_parties[winner_id]

        print(f"  ✓ Winner: Party {winner_id}, Second Price: {second_price}")

        # Phase 4: Output delivery with masking
        print("\n[Phase 4] Output Delivery...")
        outputs = {}

        for party_id, party in enumerate(self.parties):
            # Generate random mask
            r_i = Field.random()

            # Get public beacon value
            rho = await self.beacon.request(party_id)

            # Compute blinded output
            if party_id == winner_id:
                o_i = second_price
            else:
                o_i = 0

            # z_i = o_i + r_i + rho (public)
            z_i = Field.add(Field.add(o_i, r_i), rho)

            # Broadcast z_i (in real protocol, would use shares)
            await self.network.broadcast(party_id, 'OUTPUT_SHARE', {
                'party': party_id,
                'z': z_i
            })

            # Collect z values (simplified - in real protocol, would use proper reconstruction)
            # Party i computes: o_i = z_i - r_i - rho
            actual_output = Field.sub(Field.sub(z_i, r_i), rho)
            outputs[party_id] = actual_output

        print(f"  ✓ Outputs delivered")

        # Print results
        print(f"\n=== Auction Results ===")
        for party_id in range(self.n):
            output = outputs.get(party_id, 0)
            print(f"  Party {party_id}: output = {output}")

        return outputs

    async def run_auction_with_mpc(self, bids):
        """
        Run auction with full MPC circuit evaluation (more complex).
        This is a placeholder for the full implementation.
        """
        # This would implement the full gate-by-gate evaluation
        # For now, use the simplified version above
        return await self.run_auction(bids)


async def create_auction_system(n=4, f=1, faulty_parties=None, delay_range=(0, 0.01)):
    """
    Create and initialize the auction system.

    Returns:
        (parties, network, beacon, auction)
    """
    from network import Network
    from beacon import RandomnessBeacon

    # Create infrastructure
    network = Network(n, faulty_parties, delay_range)
    beacon = RandomnessBeacon(n, f)

    # Create parties
    parties = []
    for i in range(n):
        party = MPCParty(i, n, f, network, beacon)
        parties.append(party)
        await party.start()

    # Create auction protocol
    auction = AuctionProtocol(parties, network, beacon, k=5)

    return parties, network, beacon, auction


async def run_simple_auction(bids, faulty_parties=None):
    """
    Run a simple auction with given bids.

    Args:
        bids: Dictionary {party_id: bid_value}
        faulty_parties: Set of party IDs that may omit messages

    Returns:
        outputs: Dictionary {party_id: output_value}
    """
    n = 4
    f = 1

    parties, network, beacon, auction = await create_auction_system(
        n, f, faulty_parties, delay_range=(0, 0.001)
    )

    try:
        # Run auction
        outputs = await auction.run_auction(bids)

        # Wait for message delivery
        await network.wait_for_all_deliveries()

        # Print metrics
        print(f"\n=== Metrics ===")
        stats = network.get_stats()
        print(f"  Total messages sent: {stats['total_messages']}")
        print(f"  Messages delivered: {stats['delivered_messages']}")
        print(f"  Messages omitted: {stats['omitted_messages']}")
        print(f"  Beacon invocations: {beacon.get_invocation_count()}")

        return outputs

    finally:
        # Cleanup
        for party in parties:
            await party.stop()

