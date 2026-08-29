# School Redistricting Optimization with Gurobi

A mixed-integer optimization toolkit for assigning neighborhood-grade cohorts to schools while balancing travel distance, capacity, continuity, sibling co-location, utilization, and optional socioeconomic-balance penalties.

> **License notice:** this repository is source-available for non-commercial use only. Commercial use is prohibited unless separately licensed in writing. See `LICENSE`.

## Model scope

The decision variable `x[n, s, g]` assigns an entire `(neighborhood, grade)` cohort to one school. It does **not** assign individual students independently.

The model supports:

- exactly-one-school assignment per cohort;
- school/grade capacity and utilization limits;
- school opening decisions and minimum class sizes;
- maximum travel-distance restrictions;
- continuity rewards for prior assignments;
- sibling co-location rewards;
- grade-progression switching penalties;
- optional socioeconomic-balance deviation penalties.

## Installation

Python 3.10+ is recommended.

```bash
python -m pip install -e .
```

Gurobi requires its own valid installation and license. See Gurobi's official licensing documentation for your environment.

For development:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Quick start

```python
from school_redistricting import SchoolRedistrictingModel

model = SchoolRedistrictingModel()
model.build_model()
status = model.solve(verbose=False)
print(status)
print(model.get_results())
```

Run the included example with:

```bash
python examples/basic_example.py
```

## Package layout

- `src/school_redistricting/model.py` — core Gurobi model.
- `src/school_redistricting/constraints.py` — optional constraint extensions.
- `src/school_redistricting/validation.py` — input validation independent of Gurobi.
- `tests/` — validation and solver-aware tests.
- `.github/workflows/ci.yml` — lint, compile and test workflow.

## Important implementation notes

This version deliberately fixes several issues in the original prototype:

1. derived sets are created before optional defaults that depend on them;
2. socioeconomic balance is represented with linear absolute-deviation variables instead of a bilinear average constraint;
3. grade-switch variables are created only for actual cross-school transitions;
4. extension objective terms are accumulated explicitly rather than repeatedly overwriting the objective;
5. sensitivity and multi-year helpers preserve the supplied model data instead of silently reverting to unrelated defaults.

## Provenance

The initial prototype supplied for this repository contained the header `Author: Claude` and was dated April 11, 2025. This repository preserves that provenance rather than representing AI-generated source as solely human-authored. The code has subsequently been reviewed, reorganized, corrected, tested, and documented for this repository.

## Commercial licensing

The bundled license prohibits commercial use, including use in paid services, commercial SaaS/API products, internal business operations, consulting deliverables, resale, or commercial derivative works. For commercial licensing, contact the repository owner.
