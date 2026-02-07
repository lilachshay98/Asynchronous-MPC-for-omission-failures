"""
Simplified Second-Price Auction Protocol using MPC.
This is a working implementation that demonstrates the key concepts.
"""

import asyncio
from field import Field
from circuit import ArithmeticCircuit


class SimplifiedAuction:
    """
    Simplified auction protocol that demonstrates MPC concepts
    without full asynchronous complexity.
    """

    def __init__(self, n=4, f=1, k=5):
        self.n = n
        self.f = f
        self.k = k
        self.message_count = 0
        self.beacon_count = 0

    async def run_auction(self, bids):
        """
        Run the auction protocol.

        Args:
            bids: Dictionary {party_id: bid_value}

        Returns:
            outputs: Dictionary {party_id: output_value}
        """
        print(f"\n{'='*60}")
        print(f"Starting Second-Price Auction")
        print(f"{'='*60}")
        print(f"Bids: {bids}")

        # Phase 1: Input Sharing (Simulated)
        print(f"\n[Phase 1] Input Sharing")
        print(f"  Each party shares {self.k} bit values")

        # Each party shares k bits
        for party_id in range(self.n):
            if party_id in bids:
                # Share k bits per party
                self.message_count += self.k * self.n  # Each bit shared with n parties

        print(f"  Messages sent: {self.message_count}")

        # Phase 2: Agreement on Input Set
        print(f"\n[Phase 2] Agreement on Input Set (ACS)")

        # Simulate RBC for n parties (each broadcasts)
        # RBC uses VAL, ECHO, READY messages
        rbc_messages_per_party = self.n * 3  # VAL + ECHO + READY (simplified)
        self.message_count += self.n * rbc_messages_per_party

        # Simulate ABA for n parties
        # Each ABA runs multiple rounds with EST and AUX messages
        aba_rounds = 2  # Expected rounds
        aba_messages_per_round = self.n * 2  # EST + AUX
        self.message_count += self.n * aba_rounds * aba_messages_per_round
        self.beacon_count += aba_rounds * self.n  # Beacon used in ABA

        # Select n-f = 3 parties
        participating = sorted([p for p in bids.keys()])[:self.n - self.f]
        print(f"  Participating parties: {participating}")
        print(f"  Messages sent: {self.message_count}")
        print(f"  Beacon invocations: {self.beacon_count}")

        # Phase 3: Circuit Evaluation
        print(f"\n[Phase 3] Circuit Evaluation")

        # Compute auction using arithmetic circuit
        participating_bids = [bids[p] for p in participating]
        winner_idx, second_price = ArithmeticCircuit.second_price_auction(
            participating_bids, self.k
        )
        winner_id = participating[winner_idx]

        # Count circuit operations
        additions, multiplications = ArithmeticCircuit.count_operations(
            len(participating), self.k
        )

        print(f"  Circuit operations:")
        print(f"    Additions: {additions}")
        print(f"    Multiplications: {multiplications}")

        # Each multiplication requires degree reduction
        # Simplified: each mult needs n broadcasts for shares + ACS
        mult_messages = multiplications * self.n * 2  # Share + reconstruct
        self.message_count += mult_messages

        print(f"  Winner: Party {winner_id}")
        print(f"  Second price: {second_price}")
        print(f"  Messages sent: {self.message_count}")

        # Phase 4: Output Delivery
        print(f"\n[Phase 4] Output Delivery with Masking")

        # Each party creates masked output
        outputs = {}
        for party_id in range(self.n):
            # Generate random mask (simulated)
            r_i = Field.random()

            # Get beacon value (simulated)
            self.beacon_count += 1
            rho = Field.random()  # Simulated beacon

            # Compute output
            if party_id == winner_id:
                o_i = second_price
            else:
                o_i = 0

            # Blinded value: z_i = o_i + r_i + rho
            z_i = Field.add(Field.add(o_i, r_i), rho)

            # Broadcast z_i (in shares - simulated)
            self.message_count += self.n

            # Party i unblocks: o_i = z_i - r_i - rho
            actual_output = Field.sub(Field.sub(z_i, r_i), rho)
            outputs[party_id] = actual_output

        print(f"  Messages sent: {self.message_count}")
        print(f"  Beacon invocations: {self.beacon_count}")

        # Print results
        print(f"\n{'='*60}")
        print(f"Auction Results")
        print(f"{'='*60}")
        for party_id in range(self.n):
            output = outputs.get(party_id, 0)
            status = "WINNER" if output > 0 else "non-winner"
            print(f"  Party {party_id}: {status}, output = {output}")

        print(f"\n{'='*60}")
        print(f"Final Metrics")
        print(f"{'='*60}")
        print(f"  Total messages: {self.message_count}")
        print(f"  Beacon invocations: {self.beacon_count}")
        print(f"{'='*60}\n")

        return outputs


async def run_auction(bids, n=4, f=1):
    """Run a simplified auction."""
    auction = SimplifiedAuction(n, f)
    return await auction.run_auction(bids)

