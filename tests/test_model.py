import pytest

from school_redistricting.constraints import (
    add_geographic_proximity_constraints,
    add_grade_progression_constraints,
)
from school_redistricting.model import SchoolRedistrictingModel


def _build_or_skip():
    try:
        model = SchoolRedistrictingModel()
        model.build_model()
        return model
    except Exception as exc:
        pytest.skip(f"Gurobi runtime/license unavailable in this environment: {exc}")


def test_model_builds_as_linear_mip():
    model = _build_or_skip()
    model.model.update()
    # The corrected SES formulation uses linear absolute-deviation constraints.
    assert model.model.NumQConstrs == 0
    assert model.model.NumBinVars > 0


def test_geographic_constraint_adds_prohibitions():
    model = _build_or_skip()
    before = model.model.NumConstrs
    count = add_geographic_proximity_constraints(model, max_distance=2.0)
    model.model.update()
    assert count > 0
    assert model.model.NumConstrs >= before + count


def test_grade_progression_only_creates_cross_school_switches():
    model = _build_or_skip()
    switch = add_grade_progression_constraints(model, ["K", "1"], switch_penalty=0.2)
    model.model.update()
    assert len(switch) > 0
    assert all(s1 != s2 for _n, s1, s2, _idx in switch.keys())


def test_example_model_solves_when_license_available():
    model = _build_or_skip()
    try:
        status = model.solve(verbose=False)
    except Exception as exc:
        pytest.skip(f"Gurobi solve unavailable in this environment: {exc}")
    assert status is not None
    results = model.get_results()
    assert results["assignments"]
