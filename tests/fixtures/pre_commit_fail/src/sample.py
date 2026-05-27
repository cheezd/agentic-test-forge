"""Module with high-CRAP function for gate-failure fixture."""


def complex_uncovered(value: int) -> int:
    if value > 0:
        if value > 10:
            if value > 100:
                return value * 3
            return value * 2
        return value
    if value < 0:
        return -value
    return 0
