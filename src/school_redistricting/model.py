"""Core school redistricting model.

Initial prototype provenance: generated with Claude, dated 2025-04-11.
This version was reorganized and corrected for this repository.
"""

from __future__ import annotations

from copy import deepcopy

from gurobipy import GRB, Model, quicksum

from .validation import validate_data


class SchoolRedistrictingModel:
    """Assign neighborhood-grade cohorts to schools using mixed-integer optimization."""

    def __init__(self, data: dict | None = None):
        self.model: Model | None = None
        self.x = None
        self.open_s = None
        self.same_school = None
        self._extra_objective_terms = []

        if data is None:
            data = self.example_data()
        self.load_data(data)

    @staticmethod
    def example_data() -> dict:
        return {
            "students": {
                ("Neighborhood1", "K"): 30,
                ("Neighborhood1", "1"): 25,
                ("Neighborhood2", "K"): 28,
                ("Neighborhood2", "1"): 22,
                ("Neighborhood3", "K"): 15,
                ("Neighborhood3", "1"): 18,
                ("Neighborhood4", "K"): 20,
                ("Neighborhood4", "1"): 22,
            },
            "capacities": {
                ("School1", "K"): 60,
                ("School1", "1"): 60,
                ("School2", "K"): 60,
                ("School2", "1"): 60,
                ("School3", "K"): 60,
                ("School3", "1"): 60,
            },
            "schools_serving_grades": {
                "School1": ["K", "1"],
                "School2": ["K", "1"],
                "School3": ["K", "1"],
            },
            "distances": {
                ("Neighborhood1", "School1"): 2.0,
                ("Neighborhood1", "School2"): 3.0,
                ("Neighborhood1", "School3"): 4.5,
                ("Neighborhood2", "School1"): 1.5,
                ("Neighborhood2", "School2"): 2.5,
                ("Neighborhood2", "School3"): 3.0,
                ("Neighborhood3", "School1"): 3.5,
                ("Neighborhood3", "School2"): 1.8,
                ("Neighborhood3", "School3"): 2.2,
                ("Neighborhood4", "School1"): 4.2,
                ("Neighborhood4", "School2"): 3.7,
                ("Neighborhood4", "School3"): 1.5,
            },
            "previous_assignment": {
                ("Neighborhood1", "School1", "K"): 1,
                ("Neighborhood1", "School1", "1"): 1,
                ("Neighborhood2", "School2", "K"): 1,
                ("Neighborhood2", "School2", "1"): 1,
                ("Neighborhood3", "School3", "K"): 1,
                ("Neighborhood3", "School3", "1"): 1,
                ("Neighborhood4", "School1", "K"): 1,
                ("Neighborhood4", "School2", "1"): 1,
            },
            "school_costs": {"School1": 500000, "School2": 600000, "School3": 450000},
            "socioeconomic_status": {
                "Neighborhood1": 0.25,
                "Neighborhood2": 0.60,
                "Neighborhood3": 0.15,
                "Neighborhood4": 0.80,
            },
            "siblings": {
                ("Neighborhood1", "K", "1"): 5,
                ("Neighborhood2", "K", "1"): 4,
                ("Neighborhood3", "K", "1"): 3,
                ("Neighborhood4", "K", "1"): 6,
            },
            "parameters": {
                "min_class_size": 0,
                "school_open_penalty": 10.0,
                "continuity_bonus": 0.1,
                "socioeconomic_weight": 0.2,
                "distance_penalty": 1.0,
                "sibling_bonus": 0.15,
                "max_utilization": 1.0,
            },
        }

    def load_data(self, data: dict) -> None:
        validate_data(data)
        self.data = deepcopy(data)
        self.students = deepcopy(data["students"])
        self.capacities = deepcopy(data["capacities"])
        self.distances = deepcopy(data["distances"])
        self.schools_serving_grades = deepcopy(data["schools_serving_grades"])
        self._derive_sets()

        self.previous_assignment = deepcopy(data.get("previous_assignment", {}))
        self.school_costs = deepcopy(data.get("school_costs", {s: 500000 for s in self.schools}))
        self.socioeconomic_status = deepcopy(
            data.get("socioeconomic_status", {n: 0.5 for n in self.neighborhoods})
        )
        self.siblings = deepcopy(data.get("siblings", {}))

        params = data.get("parameters", {})
        self.min_class_size = params.get("min_class_size", 0)
        self.school_open_penalty = params.get("school_open_penalty", 10.0)
        self.continuity_bonus = params.get("continuity_bonus", 0.1)
        self.socioeconomic_weight = params.get("socioeconomic_weight", 0.0)
        self.distance_penalty = params.get("distance_penalty", 1.0)
        self.sibling_bonus = params.get("sibling_bonus", 0.15)
        self.max_utilization = params.get("max_utilization", 0.95)

    def _derive_sets(self) -> None:
        self.neighborhoods = sorted({n for n, _ in self.students})
        self.schools = sorted({s for s, _ in self.capacities})
        self.grades = sorted({g for _, g in self.students})
        self.valid_assignments = [
            (n, s, g)
            for n in self.neighborhoods
            for s in self.schools
            for g in self.grades
            if (n, g) in self.students and (s, g) in self.capacities
        ]

    def add_objective_term(self, expression) -> None:
        self._extra_objective_terms.append(expression)

    def build_model(self) -> Model:
        self.model = Model("SchoolRedistricting")
        self._extra_objective_terms = []
        self._create_variables()
        self._add_constraints()
        self._set_objective()
        return self.model

    def _create_variables(self) -> None:
        self.x = self.model.addVars(self.valid_assignments, vtype=GRB.BINARY, name="assignment")
        self.open_s = self.model.addVars(self.schools, vtype=GRB.BINARY, name="open")
        sibling_keys = [
            (n, s, g1, g2)
            for (n, g1, g2), _count in self.siblings.items()
            for s in self.schools
            if (n, s, g1) in self.x and (n, s, g2) in self.x
        ]
        self.same_school = self.model.addVars(sibling_keys, vtype=GRB.BINARY, name="same_school")

    def _set_objective(self) -> None:
        distance_cost = quicksum(
            self.distance_penalty * self.distances[n, s] * self.students[n, g] * self.x[n, s, g]
            for n, s, g in self.valid_assignments
        )
        continuity_reward = quicksum(
            self.continuity_bonus
            * self.previous_assignment.get((n, s, g), 0)
            * self.students[n, g]
            * self.x[n, s, g]
            for n, s, g in self.valid_assignments
        )
        opening_cost = quicksum(
            self.school_open_penalty * self.school_costs.get(s, 500000) / 500000 * self.open_s[s]
            for s in self.schools
        )
        sibling_reward = quicksum(
            self.sibling_bonus * self.siblings[n, g1, g2] * self.same_school[n, s, g1, g2]
            for n, s, g1, g2 in self.same_school.keys()
        )
        extra = quicksum(self._extra_objective_terms) if self._extra_objective_terms else 0
        self.model.setObjective(distance_cost + opening_cost - continuity_reward - sibling_reward + extra, GRB.MINIMIZE)

    def _add_constraints(self) -> None:
        for n in self.neighborhoods:
            for g in self.grades:
                choices = [self.x[n, s, g] for s in self.schools if (n, s, g) in self.x]
                if choices:
                    self.model.addConstr(quicksum(choices) == 1, name=f"assign_{n}_{g}")

        for s in self.schools:
            for g in self.grades:
                if (s, g) not in self.capacities:
                    continue
                enrollment = quicksum(
                    self.students[n, g] * self.x[n, s, g]
                    for n in self.neighborhoods
                    if (n, s, g) in self.x
                )
                self.model.addConstr(
                    enrollment <= self.capacities[s, g] * self.max_utilization,
                    name=f"capacity_{s}_{g}",
                )
                if self.min_class_size > 0:
                    self.model.addConstr(
                        enrollment >= self.min_class_size * self.open_s[s],
                        name=f"min_class_{s}_{g}",
                    )

        for n, s, g in self.valid_assignments:
            if g not in self.schools_serving_grades.get(s, []):
                self.model.addConstr(self.x[n, s, g] == 0, name=f"grade_service_{n}_{s}_{g}")
            self.model.addConstr(self.x[n, s, g] <= self.open_s[s], name=f"open_{n}_{s}_{g}")

        for n, s, g1, g2 in self.same_school.keys():
            y = self.same_school[n, s, g1, g2]
            self.model.addConstr(y <= self.x[n, s, g1])
            self.model.addConstr(y <= self.x[n, s, g2])
            self.model.addConstr(y >= self.x[n, s, g1] + self.x[n, s, g2] - 1)

        self._add_socioeconomic_balance_penalty()

    def _add_socioeconomic_balance_penalty(self) -> None:
        if self.socioeconomic_weight <= 0 or not self.socioeconomic_status:
            return
        total_students = sum(self.students.values())
        district_avg = sum(
            self.socioeconomic_status.get(n, 0.5) * count
            for (n, _g), count in self.students.items()
        ) / total_students

        deviations = []
        for s in self.schools:
            for g in self.grades:
                if (s, g) not in self.capacities:
                    continue
                positive = self.model.addVar(lb=0.0, name=f"ses_pos_{s}_{g}")
                negative = self.model.addVar(lb=0.0, name=f"ses_neg_{s}_{g}")
                weighted_gap = quicksum(
                    (self.socioeconomic_status.get(n, 0.5) - district_avg)
                    * self.students[n, g]
                    * self.x[n, s, g]
                    for n in self.neighborhoods
                    if (n, s, g) in self.x
                )
                self.model.addConstr(weighted_gap == positive - negative, name=f"ses_gap_{s}_{g}")
                deviations.extend([positive, negative])
        if deviations:
            self.add_objective_term(self.socioeconomic_weight * quicksum(deviations))

    def solve(self, time_limit: float | None = None, gap: float | None = None, verbose: bool = True):
        if self.model is None:
            self.build_model()
        if time_limit is not None:
            self.model.setParam("TimeLimit", time_limit)
        if gap is not None:
            self.model.setParam("MIPGap", gap)
        if not verbose:
            self.model.setParam("OutputFlag", 0)
        self.model.optimize()
        return self.model.status

    def get_results(self) -> dict:
        if self.model is None or self.model.SolCount == 0:
            return {"status": "No solution", "assignments": {}, "open_schools": []}

        assignments = {}
        for n, s, g in self.valid_assignments:
            if self.x[n, s, g].X > 0.5:
                assignments[f"{n}_{g}"] = {
                    "neighborhood": n,
                    "grade": g,
                    "school": s,
                    "students": self.students[n, g],
                    "distance": self.distances[n, s],
                }
        return {
            "status": "Optimal" if self.model.status == GRB.OPTIMAL else "Feasible",
            "status_code": self.model.status,
            "objective_value": self.model.ObjVal,
            "assignments": assignments,
            "open_schools": [s for s in self.schools if self.open_s[s].X > 0.5],
        }

    def clone_data(self) -> dict:
        return deepcopy(self.data)
