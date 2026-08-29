"""Basic executable example."""

from school_redistricting import SchoolRedistrictingModel
from school_redistricting.constraints import add_geographic_proximity_constraints


def main():
    model = SchoolRedistrictingModel()
    model.build_model()
    add_geographic_proximity_constraints(model, max_distance=5.0)
    model.solve(verbose=True)
    results = model.get_results()
    print(f"Status: {results['status']}")
    print(f"Objective: {results.get('objective_value')}")
    for assignment in results["assignments"].values():
        print(
            f"{assignment['neighborhood']} grade {assignment['grade']} -> "
            f"{assignment['school']} ({assignment['students']} students)"
        )


if __name__ == "__main__":
    main()
