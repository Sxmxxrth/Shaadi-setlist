"""Tests for the mashup planner."""

import pytest

from src.mashup_planner import build_mashup_plan, get_energy

CASES = [
    ("baraat, hype, punjabi, gen-z", 6, "rising"),
    ("haldi, fun, family", 6, "rising"),
    ("bidaai, emotional, family", 5, "soft"),
]


def is_mostly_rising(values: list[int]) -> bool:
    drops = sum(1 for current, next_value in zip(values, values[1:]) if next_value < current)
    return drops <= 1


@pytest.mark.parametrize("user_input, length, expected_shape", CASES)
def test_mashup_planner(user_input, length, expected_shape):
    plan = build_mashup_plan(user_input, length=length)
    energy_values = [get_energy(song) for song in plan["songs"]]

    assert len(plan["songs"]) == length, f"expected {length} songs, got {len(plan['songs'])}"
    assert len(plan["transitions"]) == length - 1, f"expected {length - 1} transitions, got {len(plan['transitions'])}"

    if expected_shape == "rising":
        assert is_mostly_rising(energy_values), f"expected mostly rising energy, got {energy_values}"
    elif expected_shape == "soft":
        assert max(energy_values) <= 5, f"expected soft energy, got {energy_values}"
