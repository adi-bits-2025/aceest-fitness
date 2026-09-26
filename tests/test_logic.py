"""Unit tests for the pure business-logic functions in app.py."""
import random
from datetime import date

import pytest

from app import (PROGRAM_TEMPLATES, calculate_bmi, calculate_calories,
                 generate_program, membership_status)


# ---------- calories ----------
@pytest.mark.parametrize("program, expected", [
    ("Fat Loss", 80 * 22),
    ("Muscle Gain", 80 * 35),
    ("Beginner", 80 * 26),
])
def test_calories_use_program_factor(program, expected):
    assert calculate_calories(80, program) == expected


def test_calories_are_whole_numbers():
    assert calculate_calories(70.5, "Fat Loss") == 1551  # int(70.5 * 22)


def test_calories_unknown_program():
    with pytest.raises(ValueError):
        calculate_calories(80, "Yoga")


@pytest.mark.parametrize("weight", [0, -5, None])
def test_calories_invalid_weight(weight):
    with pytest.raises(ValueError):
        calculate_calories(weight, "Fat Loss")


# ---------- BMI ----------
@pytest.mark.parametrize("height, weight, bmi, category", [
    (175, 50, 16.3, "Underweight"),
    (175, 70, 22.9, "Normal"),
    (175, 80, 26.1, "Overweight"),
    (175, 100, 32.7, "Obese"),
])
def test_bmi_categories(height, weight, bmi, category):
    assert calculate_bmi(height, weight) == (bmi, category)


def test_bmi_boundary_values():
    # 18.5 and 25.0 fall into the next category up
    assert calculate_bmi(100, 18.5)[1] == "Normal"
    assert calculate_bmi(100, 25)[1] == "Overweight"
    assert calculate_bmi(100, 30)[1] == "Obese"


@pytest.mark.parametrize("height, weight", [(0, 70), (175, 0), (None, 70), (-1, 70)])
def test_bmi_invalid_input(height, weight):
    with pytest.raises(ValueError):
        calculate_bmi(height, weight)


# ---------- membership ----------
TODAY = date(2026, 6, 15)


def test_membership_active():
    assert membership_status("2026-12-31", today=TODAY) == "Active"


def test_membership_active_on_last_day():
    assert membership_status("2026-06-15", today=TODAY) == "Active"


def test_membership_expired():
    assert membership_status("2026-06-14", today=TODAY) == "Expired"


@pytest.mark.parametrize("end", [None, ""])
def test_membership_not_set(end):
    assert membership_status(end, today=TODAY) == "N/A"


def test_membership_invalid_date():
    with pytest.raises(ValueError):
        membership_status("not-a-date", today=TODAY)


# ---------- program generator ----------
@pytest.mark.parametrize("program", list(PROGRAM_TEMPLATES))
def test_generate_program_for_type(program):
    ptype, plan = generate_program(program)
    assert ptype == program
    assert plan in PROGRAM_TEMPLATES[program]


def test_generate_program_random_type_is_valid():
    ptype, plan = generate_program(rng=random.Random(42))
    assert ptype in PROGRAM_TEMPLATES
    assert plan in PROGRAM_TEMPLATES[ptype]


def test_generate_program_is_deterministic_with_seed():
    assert generate_program(rng=random.Random(7)) == generate_program(rng=random.Random(7))


def test_generate_program_unknown_type():
    with pytest.raises(ValueError):
        generate_program("Yoga")
