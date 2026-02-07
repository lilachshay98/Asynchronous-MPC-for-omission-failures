"""
Arithmetic circuit evaluation with secret sharing.
Implements bit decomposition, comparison, and max gadgets.
"""

from field import Field, Polynomial


class ArithmeticCircuit:
    """
    Arithmetic circuit for second-price auction.
    Supports addition, multiplication, comparison, and max operations.
    """

    @staticmethod
    def bit_decompose(value, k=5):
        """
        Decompose value into k bits.
        Returns list of bits [b_0, b_1, ..., b_{k-1}] where value = sum(b_i * 2^i).
        """
        bits = []
        for i in range(k):
            bits.append((value >> i) & 1)
        return bits

    @staticmethod
    def compare_bits(a_bits, b_bits):
        """
        Compare two k-bit numbers.
        Returns 1 if a > b, 0 otherwise.
        Uses secret-shared bit arithmetic.

        Formula: c = sum_{j=k-1}^{0} (a_j * (1 - b_j)) * prod_{l=j+1}^{k-1} (1 - (a_l - b_l)^2)
        """
        k = len(a_bits)
        result = 0

        for j in range(k - 1, -1, -1):
            # Compute (a_j * (1 - b_j))
            term = Field.mul(a_bits[j], Field.sub(1, b_bits[j]))

            # Compute enable flag: prod_{l=j+1}^{k-1} (1 - (a_l - b_l)^2)
            enable = 1
            for l in range(j + 1, k):
                diff = Field.sub(a_bits[l], b_bits[l])
                diff_sq = Field.mul(diff, diff)
                enable = Field.mul(enable, Field.sub(1, diff_sq))

            # Add to result
            result = Field.add(result, Field.mul(term, enable))

        return result

    @staticmethod
    def max_two(a, b, a_bits, b_bits):
        """
        Compute max(a, b) using comparison bit.
        Returns max(a, b).

        Formula: max(a,b) = c*a + (1-c)*b where c = (a > b)
        """
        c = ArithmeticCircuit.compare_bits(a_bits, b_bits)
        # max = c*a + (1-c)*b
        term1 = Field.mul(c, a)
        term2 = Field.mul(Field.sub(1, c), b)
        return Field.add(term1, term2)

    @staticmethod
    def find_max(values, k=5):
        """
        Find maximum value using tournament tree.
        Returns (max_value, winner_index).
        """
        n = len(values)
        if n == 0:
            return (0, -1)
        if n == 1:
            return (values[0], 0)

        # Bit decompose all values
        all_bits = [ArithmeticCircuit.bit_decompose(v, k) for v in values]

        # Tournament tree
        current_values = list(values)
        current_indices = list(range(n))
        current_bits = all_bits

        while len(current_values) > 1:
            next_values = []
            next_indices = []
            next_bits = []

            for i in range(0, len(current_values), 2):
                if i + 1 < len(current_values):
                    # Compare two values
                    max_val = ArithmeticCircuit.max_two(
                        current_values[i], current_values[i + 1],
                        current_bits[i], current_bits[i + 1]
                    )
                    # Determine which was larger
                    if max_val == current_values[i]:
                        next_values.append(current_values[i])
                        next_indices.append(current_indices[i])
                        next_bits.append(current_bits[i])
                    else:
                        next_values.append(current_values[i + 1])
                        next_indices.append(current_indices[i + 1])
                        next_bits.append(current_bits[i + 1])
                else:
                    # Odd one out
                    next_values.append(current_values[i])
                    next_indices.append(current_indices[i])
                    next_bits.append(current_bits[i])

            current_values = next_values
            current_indices = next_indices
            current_bits = next_bits

        return (current_values[0], current_indices[0])

    @staticmethod
    def find_second_max(values, winner_idx, k=5):
        """
        Find second maximum by masking winner and finding max again.
        Returns second_max_value.
        """
        # Create masked values: x'_i = (1 - chi_i) * x_i
        masked_values = []
        for i, v in enumerate(values):
            if i == winner_idx:
                masked_values.append(0)  # Mask the winner
            else:
                masked_values.append(v)

        # Find max of masked values
        second_max, _ = ArithmeticCircuit.find_max(masked_values, k)
        return second_max

    @staticmethod
    def second_price_auction(bids, k=5):
        """
        Compute second-price auction outcome.
        bids: list of bid values
        Returns: (winner_id, second_price)
        """
        # Find winner
        max_bid, winner_id = ArithmeticCircuit.find_max(bids, k)

        # Find second price
        second_price = ArithmeticCircuit.find_second_max(bids, winner_id, k)

        return (winner_id, second_price)

    @staticmethod
    def count_operations(n, k):
        """
        Count total additions and multiplications for the auction circuit.

        Returns: (num_additions, num_multiplications)
        """
        # Comparison gadget: O(k) multiplications
        # Finding max of n elements: O(n) comparisons
        # Two max operations (winner + second price)

        multiplications = 2 * n * k  # Rough estimate
        additions = 2 * n * k

        return (additions, multiplications)

