"""
Agreement on Common Set (ACS) protocol.
Combines RBC and ABA to agree on n-f valid inputs.
"""

import asyncio
from rbc import ReliableBroadcast
from aba import BinaryAgreement


class AgreementOnCommonSet:
    """
    Agreement on Common Set using RBC + ABA.
    Ensures all parties agree on the same set of n-f inputs.
    """

    def __init__(self, party_id, n, f, network, beacon):
        self.party_id = party_id
        self.n = n
        self.f = f
        self.network = network
        self.beacon = beacon

        # RBC instances
        self.rbc = ReliableBroadcast(party_id, n, f, network)

        # ABA instances per party
        self.abas = {}

        # Delivered RBC values
        self.delivered_rbcs = set()

    async def propose(self, value):
        """
        Propose a value to be included in the common set.
        Returns the agreed upon set of n-f values.
        """
        # Phase 1: Broadcast my value using RBC
        await self.rbc.broadcast(value)

        # Phase 2: Wait for n-f RBC deliveries
        asyncio.create_task(self._monitor_rbc_deliveries())

        while len(self.delivered_rbcs) < self.n - self.f:
            await asyncio.sleep(0.001)

        # Phase 3: Run ABA for each party
        aba_results = {}
        aba_tasks = []

        for i in range(self.n):
            # Propose 1 if I've delivered RBC_i, else 0
            proposal = 1 if i in self.delivered_rbcs else 0

            aba = BinaryAgreement(self.party_id, self.n, self.f,
                                 self.network, self.beacon, instance_id=i)
            self.abas[i] = aba

            # Start ABA
            task = asyncio.create_task(self._run_aba(i, aba, proposal))
            aba_tasks.append(task)

        # Wait for all ABAs to complete
        results = await asyncio.gather(*aba_tasks)

        for i, result in enumerate(results):
            aba_results[i] = result

        # Phase 4: Collect the set S of parties with ABA output 1
        S = {i for i in range(self.n) if aba_results[i] == 1}

        # Ensure we have at least n-f parties
        assert len(S) >= self.n - self.f, f"ACS: Not enough parties in S: {len(S)}"

        # Select exactly n-f parties (first n-f by ID)
        V = sorted(S)[: self.n - self.f]

        # Wait for any pending RBCs in V
        for i in V:
            if i not in self.delivered_rbcs:
                await self.rbc.deliver(i)
                self.delivered_rbcs.add(i)

        # Collect values
        result_set = {}
        for i in V:
            value = await self.rbc.deliver(i)
            result_set[i] = value

        return result_set

    async def _monitor_rbc_deliveries(self):
        """Monitor and track RBC deliveries."""
        for i in range(self.n):
            if i not in self.delivered_rbcs:
                asyncio.create_task(self._wait_for_rbc(i))

    async def _wait_for_rbc(self, sender):
        """Wait for RBC from sender to deliver."""
        try:
            await self.rbc.deliver(sender)
            self.delivered_rbcs.add(sender)
        except:
            pass

    async def _run_aba(self, instance_id, aba, proposal):
        """Run an ABA instance."""
        return await aba.propose(proposal)

    async def handle_message(self, message):
        """Process ACS-related messages."""
        msg_type = message.msg_type

        if msg_type.startswith('RBC_'):
            await self.rbc.handle_message(message)
        elif msg_type.startswith('ABA_'):
            # Route to appropriate ABA instance
            instance = message.payload.get('instance')
            if instance in self.abas:
                await self.abas[instance].handle_message(message)

