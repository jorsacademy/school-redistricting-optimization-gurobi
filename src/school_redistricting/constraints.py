"""Optional constraint extensions for school redistricting models."""

from __future__ import annotations

from gurobipy import GRB, quicksum


def add_grade_progression_constraints(redistricting_model, grades_ordered, switch_penalty=0.1):
    """Penalize moving a cohort between different schools in consecutive grades."""
    model = redistricting_model.model
    x = redistricting_model.x
    if model is None or x is None:
        raise RuntimeError("build_model() must be called before adding extension constraints")

    transitions = [
        (n, s1, s2, idx)
        for n in redistricting_model.neighborhoods
        for idx in range(len(grades_ordered) - 1)
        for s1 in redistricting_model.schools
        for s2 in redistricting_model.schools
        if s1 != s2
        and (n, s1, grades_ordered[idx]) in x
        and (n, s2, grades_ordered[idx + 1]) in x
    ]
    switch = model.addVars(transitions, vtype=GRB.BINARY, name="switch_school")

    for n, s1, s2, idx in transitions:
        g1, g2 = grades_ordered[idx], grades_ordered[idx + 1]
        model.addConstr(
            switch[n, s1, s2, idx] >= x[n, s1, g1] + x[n, s2, g2] - 1,
            name=f"switch_{n}_{s1}_{s2}_{g1}_{g2}",
        )

    if transitions:
        redistricting_model.add_objective_term(
            switch_penalty * quicksum(switch[key] for key in transitions)
        )
        redistricting_model._set_objective()
    return switch


def add_geographic_proximity_constraints(redistricting_model, max_distance=5.0):
    """Prohibit assignments farther than max_distance."""
    model = redistricting_model.model
    x = redistricting_model.x
    if model is None or x is None:
        raise RuntimeError("build_model() must be called before adding extension constraints")

    count = 0
    for n, s, g in redistricting_model.valid_assignments:
        if redistricting_model.distances[n, s] > max_distance:
            model.addConstr(x[n, s, g] == 0, name=f"max_dist_{n}_{s}_{g}")
            count += 1
    return count


def add_balanced_enrollment_constraints(redistricting_model, min_utilization=0.0, max_utilization=0.95):
    """Apply explicit lower/upper utilization limits to open schools by grade."""
    if not 0 <= min_utilization <= max_utilization <= 1:
        raise ValueError("utilization must satisfy 0 <= min <= max <= 1")

    model = redistricting_model.model
    x = redistricting_model.x
    if model is None or x is None:
        raise RuntimeError("build_model() must be called before adding extension constraints")

    for s in redistricting_model.schools:
        for g in redistricting_model.grades:
            if (s, g) not in redistricting_model.capacities:
                continue
            enrollment = quicksum(
                redistricting_model.students[n, g] * x[n, s, g]
                for n in redistricting_model.neighborhoods
                if (n, s, g) in x
            )
            capacity = redistricting_model.capacities[s, g]
            model.addConstr(
                enrollment <= capacity * max_utilization * redistricting_model.open_s[s],
                name=f"balanced_max_{s}_{g}",
            )
            if min_utilization > 0:
                model.addConstr(
                    enrollment >= capacity * min_utilization * redistricting_model.open_s[s],
                    name=f"balanced_min_{s}_{g}",
                )
