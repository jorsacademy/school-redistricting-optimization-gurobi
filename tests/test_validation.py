import copy

import pytest

from school_redistricting.model import SchoolRedistrictingModel
from school_redistricting.validation import validate_data


def test_example_data_is_valid():
    validate_data(SchoolRedistrictingModel.example_data())


def test_missing_required_key_is_rejected():
    data = SchoolRedistrictingModel.example_data()
    del data["distances"]
    with pytest.raises(ValueError, match="Missing required data keys"):
        validate_data(data)


def test_missing_distance_is_rejected():
    data = copy.deepcopy(SchoolRedistrictingModel.example_data())
    del data["distances"][("Neighborhood1", "School1")]
    with pytest.raises(ValueError, match="Missing neighborhood-school distances"):
        validate_data(data)


def test_optional_defaults_do_not_require_preexisting_sets():
    data = SchoolRedistrictingModel.example_data()
    for key in ["previous_assignment", "school_costs", "socioeconomic_status", "siblings"]:
        data.pop(key, None)
    model = SchoolRedistrictingModel(data)
    assert model.schools
    assert model.neighborhoods
    assert set(model.school_costs) == set(model.schools)
