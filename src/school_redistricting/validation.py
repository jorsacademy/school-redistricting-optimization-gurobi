"""Input validation helpers that do not require a solver license."""

from __future__ import annotations

from collections.abc import Mapping


def validate_data(data: Mapping) -> None:
    """Validate the minimum structure and cross-field consistency of model input."""
    required = {"students", "capacities", "distances", "schools_serving_grades"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Missing required data keys: {sorted(missing)}")

    students = data["students"]
    capacities = data["capacities"]
    distances = data["distances"]
    serving = data["schools_serving_grades"]

    if not students:
        raise ValueError("students must not be empty")
    if not capacities:
        raise ValueError("capacities must not be empty")

    for (neighborhood, grade), count in students.items():
        if count < 0:
            raise ValueError(f"Negative student count for {(neighborhood, grade)}")

    for (school, grade), capacity in capacities.items():
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive for {(school, grade)}")
        if grade not in serving.get(school, []):
            raise ValueError(f"{school} has capacity for grade {grade} but does not list it as served")

    neighborhoods = {n for n, _ in students}
    schools = {s for s, _ in capacities}

    missing_distances = [
        (n, s) for n in neighborhoods for s in schools if (n, s) not in distances
    ]
    if missing_distances:
        preview = missing_distances[:5]
        raise ValueError(f"Missing neighborhood-school distances, e.g. {preview}")

    params = data.get("parameters", {})
    min_util = params.get("min_utilization", 0.0)
    max_util = params.get("max_utilization", 0.95)
    if not 0 <= min_util <= max_util <= 1:
        raise ValueError("utilization parameters must satisfy 0 <= min <= max <= 1")
