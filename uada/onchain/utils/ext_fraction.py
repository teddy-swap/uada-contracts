from opshin.std.fractions import *


def mul_fraction_int(a: Fraction, b: int) -> Fraction:
    """returns a * b"""
    return Fraction(a.numerator * b, a.denominator)
