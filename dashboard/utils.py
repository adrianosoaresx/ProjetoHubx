from __future__ import annotations


def get_variation(previous_value: float, current_value: float) -> float:
    """Return percentage variation between values."""
    denominator = previous_value if previous_value > 1 else 1
    return (current_value - previous_value) / denominator * 100
