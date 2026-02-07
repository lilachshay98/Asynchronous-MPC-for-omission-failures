"""
Field arithmetic over prime field F_p.
We use p = 2^31 - 1 (Mersenne prime) for efficient modular arithmetic.
"""

class Field:
    """Finite field arithmetic."""

    # Using Mersenne prime for efficiency
    MODULUS = 2**31 - 1

    @classmethod
    def add(cls, a, b):
        """Add two field elements."""
        return (a + b) % cls.MODULUS

    @classmethod
    def sub(cls, a, b):
        """Subtract two field elements."""
        return (a - b) % cls.MODULUS

    @classmethod
    def mul(cls, a, b):
        """Multiply two field elements."""
        return (a * b) % cls.MODULUS

    @classmethod
    def neg(cls, a):
        """Negate a field element."""
        return (-a) % cls.MODULUS

    @classmethod
    def inv(cls, a):
        """Multiplicative inverse using Fermat's little theorem."""
        if a == 0:
            raise ValueError("Cannot invert zero")
        # a^(p-1) = 1 (mod p), so a^(-1) = a^(p-2) (mod p)
        return pow(a, cls.MODULUS - 2, cls.MODULUS)

    @classmethod
    def div(cls, a, b):
        """Divide two field elements."""
        return cls.mul(a, cls.inv(b))

    @classmethod
    def random(cls):
        """Generate a random field element."""
        import random
        return random.randint(0, cls.MODULUS - 1)

    @classmethod
    def embed(cls, x):
        """Embed an integer into the field."""
        return x % cls.MODULUS

    @classmethod
    def is_valid(cls, x):
        """Check if x is a valid field element."""
        return 0 <= x < cls.MODULUS


class Polynomial:
    """Polynomial over a finite field."""

    def __init__(self, coefficients):
        """
        Create a polynomial from coefficients.
        coefficients[i] is the coefficient of x^i.
        """
        self.coeffs = [Field.embed(c) for c in coefficients]
        # Remove leading zeros
        while len(self.coeffs) > 1 and self.coeffs[-1] == 0:
            self.coeffs.pop()

    def degree(self):
        """Return the degree of the polynomial."""
        return len(self.coeffs) - 1

    def eval(self, x):
        """Evaluate polynomial at point x using Horner's method."""
        x = Field.embed(x)
        result = 0
        for coeff in reversed(self.coeffs):
            result = Field.add(Field.mul(result, x), coeff)
        return result

    def __add__(self, other):
        """Add two polynomials."""
        max_len = max(len(self.coeffs), len(other.coeffs))
        result = []
        for i in range(max_len):
            a = self.coeffs[i] if i < len(self.coeffs) else 0
            b = other.coeffs[i] if i < len(other.coeffs) else 0
            result.append(Field.add(a, b))
        return Polynomial(result)

    def __mul__(self, other):
        """Multiply two polynomials."""
        if isinstance(other, int):
            # Scalar multiplication
            return Polynomial([Field.mul(c, other) for c in self.coeffs])

        result = [0] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i, a in enumerate(self.coeffs):
            for j, b in enumerate(other.coeffs):
                result[i + j] = Field.add(result[i + j], Field.mul(a, b))
        return Polynomial(result)

    @staticmethod
    def interpolate(points):
        """
        Lagrange interpolation.
        points: list of (x, y) tuples.
        Returns the polynomial passing through these points.
        """
        n = len(points)
        result = Polynomial([0])

        for i in range(n):
            xi, yi = points[i]
            # Build Lagrange basis polynomial L_i(x)
            basis = Polynomial([1])
            for j in range(n):
                if i != j:
                    xj = points[j][0]
                    # basis *= (x - xj) / (xi - xj)
                    numerator = Polynomial([Field.neg(xj), 1])  # x - xj
                    denominator = Field.sub(xi, xj)
                    denom_inv = Field.inv(denominator)
                    basis = basis * numerator * denom_inv

            # Add yi * basis to result
            basis = basis * yi
            result = result + basis

        return result

    @staticmethod
    def lagrange_coefficient(i, points, eval_point=0):
        """
        Compute the i-th Lagrange coefficient for interpolation at eval_point.
        points: list of x-coordinates
        """
        xi = points[i]
        result = 1
        for j, xj in enumerate(points):
            if i != j:
                # result *= (eval_point - xj) / (xi - xj)
                numerator = Field.sub(eval_point, xj)
                denominator = Field.sub(xi, xj)
                result = Field.mul(result, Field.div(numerator, denominator))
        return result

    def __repr__(self):
        return f"Polynomial({self.coeffs})"


class BiVariatePolynomial:
    """Bi-variate polynomial over finite field for BGW secret sharing."""

    def __init__(self, degree, secret=None):
        """
        Create a random bi-variate polynomial of given degree with p(0,0) = secret.
        """
        self.degree = degree
        self.coeffs = {}

        # Random coefficients except a_{0,0}
        for i in range(degree + 1):
            for j in range(degree + 1):
                if i == 0 and j == 0:
                    self.coeffs[(i, j)] = Field.embed(secret) if secret is not None else Field.random()
                else:
                    self.coeffs[(i, j)] = Field.random()

    def eval(self, x, y):
        """Evaluate p(x, y)."""
        x = Field.embed(x)
        y = Field.embed(y)
        result = 0
        for (i, j), coeff in self.coeffs.items():
            term = Field.mul(coeff, Field.mul(pow(x, i, Field.MODULUS),
                                              pow(y, j, Field.MODULUS)))
            result = Field.add(result, term)
        return result

    def row_polynomial(self, i):
        """Return the univariate polynomial p(i, y)."""
        coeffs = [0] * (self.degree + 1)
        i_pow = [pow(i, exp, Field.MODULUS) for exp in range(self.degree + 1)]

        for j in range(self.degree + 1):
            for k in range(self.degree + 1):
                term = Field.mul(self.coeffs[(k, j)], i_pow[k])
                coeffs[j] = Field.add(coeffs[j], term)

        return Polynomial(coeffs)

    def col_polynomial(self, i):
        """Return the univariate polynomial p(x, i)."""
        coeffs = [0] * (self.degree + 1)
        i_pow = [pow(i, exp, Field.MODULUS) for exp in range(self.degree + 1)]

        for j in range(self.degree + 1):
            for k in range(self.degree + 1):
                term = Field.mul(self.coeffs[(j, k)], i_pow[k])
                coeffs[j] = Field.add(coeffs[j], term)

        return Polynomial(coeffs)

    def get_secret(self):
        """Return the secret p(0, 0)."""
        return self.coeffs[(0, 0)]

