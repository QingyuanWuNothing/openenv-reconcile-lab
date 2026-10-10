"""Private formal reasoning redesign: certify a bounded integer optimum."""

import copy
from fractions import Fraction
from .scenarios import Scenario
from .math_tasks import rational, encoded
from .numeric_tools import calculate


def solve(rows):
    rows = [[rational(x) for x in row] for row in rows]
    variables = len(rows[0]) - 1
    pivots = []
    target = 0
    for column in range(variables):
        source = next((i for i in range(target, len(rows)) if rows[i][column]), None)
        if source is None:
            continue
        rows[target], rows[source] = rows[source], rows[target]
        divisor = rows[target][column]
        rows[target] = [x / divisor for x in rows[target]]
        for i, row in enumerate(rows):
            if i != target:
                factor = row[column]
                rows[i] = [a - factor * b for a, b in zip(row, rows[target])]
        pivots.append(column)
        target += 1
        if target == len(rows):
            break
    inconsistent = any(not any(row[:-1]) and row[-1] for row in rows)
    witness = [Fraction(0) for _ in range(variables)]
    for i, column in enumerate(pivots):
        witness[column] = rows[i][-1]
    return {
        "matrix": [[encoded(x) for x in row] for row in rows],
        "classification": "inconsistent"
        if inconsistent
        else "unique"
        if len(pivots) == variables
        else "underdetermined",
        "solution": [] if inconsistent else [encoded(x) for x in witness],
    }


class MathDual(Scenario):
    family = "math"

    def __init__(self, seed, level, split="train", *, variables=None, dense=None):
        super().__init__(seed, level, split)
        size = (variables if variables is not None else (2 if level == 2 else 3)) + (
            split == "holdout"
        )
        bound = 6 if split == "train" else 7
        point = [self.rng.randint(1, 4) for _ in range(size)]
        rows = []
        prices = [Fraction(self.rng.choice([1, 2, 3]), 2) for _ in range(size)]
        for i in range(size):
            coeff = [6 * self.rng.randint(-2, 2) for _ in range(size)]
            coeff[i] = sum(abs(x) for j, x in enumerate(coeff) if j != i) + 12
            if level == 2 if dense is None else not dense:
                coeff = [(12 + 2 * i) if j == i else 0 for j in range(size)]
            rhs = sum(a * x for a, x in zip(coeff, point)) - Fraction(1, 10)
            rows.append({"coefficients": coeff, "rhs": encoded(rhs)})
        costs = [
            int(sum(prices[i] * rows[i]["coefficients"][j] for i in range(size)))
            for j in range(size)
        ]
        for _ in range(2):
            coeff = [self.rng.randint(-5, 5) for _ in range(size)]
            rows.append(
                {
                    "coefficients": coeff,
                    "rhs": sum(a * x for a, x in zip(coeff, point))
                    - self.rng.randint(3, 8),
                }
            )
        for j in range(size):
            coeff = [int(i == j) for i in range(size)]
            rows.append({"coefficients": coeff, "rhs": 0})
            rows.append({"coefficients": [-x for x in coeff], "rhs": -bound})
        self.rng.shuffle(rows)
        for i, row in enumerate(rows):
            row["id"] = f"constraint-{i}"
        goal = "Find an integer vector x minimizing the integer objective costs dot x, subject to every coefficients dot x >= rhs. All variable bounds are included as constraints. Certify global integer optimality using a nonnegative multiplier per constraint: their weighted coefficient sum must equal costs, and their weighted RHS lower bound must be strictly greater than candidate_cost-1. Integer objective values then imply no strictly cheaper feasible integer point. A feasible candidate alone, negative prices, or an unverified optimality assertion earns zero. Fractions use exact {num,den} objects. Constraint order defines multiplier order. The linear-system tool solves only the matrix YOU supply; it does not choose active inequalities or an integer candidate. Inspect slacks and certificate diagnostics and adapt your selection."
        self.resources = {
            "problem": {
                "variables": [f"x{i}" for i in range(size)],
                "costs": costs,
                "constraints": rows,
                "goal": goal,
                "worked_example": "Separate toy example: constraints 2*x>=3 and 3*y>=5, objective x+y. Candidate [2,2] costs 4. Multipliers [{num:1,den:2},{num:1,den:3}] give coefficients [1,1] and lower bound 19/6>3, proving integer optimum 4. For the actual problem use its own constraints/costs; enter zero for unused constraints and preserve their published order. For a selected square basis A, solve A^T*lambda=costs; verify lambda>=0. A feasible integer candidate and the certificate must both pass.",
                "arithmetic_limit": "Absolute numerator and positive denominator <=1000000000",
            },
            "certificate": {"candidate": [], "multipliers": []},
        }
        self.instruction = "Prove an integer optimization result. Inspect the constraints, choose useful active inequalities, use exact linear algebra to construct a candidate and nonnegative bound certificate, check primal slacks and the proof, revise if necessary and commit."
        self.instruction += ' Every inequality uses >=; a row -x >= -6 is an upper bound x <= 6. Invoke numerical tools with op="run" and target="solve_linear" or "calculate", then inspect their result. Fraction objects must use quoted JSON keys "num" and "den".'
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "certificate": "params={candidate:[integers],multipliers:[number or {num,den},...]}; one multiplier per published constraint"
            },
            "run": {
                "calculate": "params={expression:string,variables:{name:number or {num,den}}}; exact +,-,*,/, powers 0..8, abs, ceil, floor, round_half_up; computes supplied numbers only",
                "solve_linear": "params={matrix:[[number or {num,den},...,rhs],...]}; 1–6 rows and 1–6 variables; exact RREF and a solution for this supplied linear system only",
                "check": "params={}; actual candidate cost, each constraint slack, weighted coefficient sum, residual against costs, weighted RHS lower bound and gap needed for the integer proof",
                "verify": "params={}; execute primal-feasibility and nonnegative integer-bound certificate checks",
            },
        }

    def patch(self, target, params):
        problem = self.resources["problem"]
        if (
            target != "certificate"
            or set(params) != {"candidate", "multipliers"}
            or not isinstance(params["candidate"], list)
            or len(params["candidate"]) != len(problem["costs"])
            or any(type(v) is not int or abs(v) > 100000 for v in params["candidate"])
            or not isinstance(params["multipliers"], list)
            or len(params["multipliers"]) != len(problem["constraints"])
        ):
            raise ValueError(
                "Provide an integer candidate and one multiplier per constraint"
            )
        values = [rational(x) for x in params["multipliers"]]
        self.resources["certificate"] = {
            "candidate": list(params["candidate"]),
            "multipliers": [encoded(x) for x in values],
        }
        self.version += 1
        return {"certificate_updated": True, "version": self.version}

    def checks(self):
        p = self.resources["problem"]
        c = self.resources["certificate"]
        x = c["candidate"]
        raw = c["multipliers"]
        complete = len(x) == len(p["costs"]) and len(raw) == len(p["constraints"])
        if not complete:
            return {
                "integer_candidate_feasible": False,
                "nonnegative_multipliers": False,
                "objective_coefficients_match": False,
                "integer_lower_bound_proves_optimum": False,
            }
        multipliers = [rational(v) for v in raw]
        feasible = all(
            sum(a * v for a, v in zip(row["coefficients"], x)) >= rational(row["rhs"])
            for row in p["constraints"]
        )
        nonnegative = all(v >= 0 for v in multipliers)
        matched = all(
            sum(
                lam * row["coefficients"][j]
                for lam, row in zip(multipliers, p["constraints"])
            )
            == cost
            for j, cost in enumerate(p["costs"])
        )
        lower = sum(
            lam * rational(row["rhs"])
            for lam, row in zip(multipliers, p["constraints"])
        )
        cost = sum(a * v for a, v in zip(p["costs"], x))
        return {
            "integer_candidate_feasible": bool(feasible),
            "nonnegative_multipliers": bool(nonnegative),
            "objective_coefficients_match": bool(matched),
            "integer_lower_bound_proves_optimum": bool(
                feasible and nonnegative and matched and lower > cost - 1
            ),
        }

    def run(self, target, params):
        if target == "calculate":
            return calculate(params)
        if target == "solve_linear":
            rows = params.get("matrix")
            if (
                set(params) != {"matrix"}
                or not isinstance(rows, list)
                or not 1 <= len(rows) <= 6
                or any(not isinstance(r, list) for r in rows)
                or not 2 <= len(rows[0]) <= 7
                or any(len(r) != len(rows[0]) for r in rows)
            ):
                raise ValueError("Provide a rectangular augmented matrix within limits")
            return solve(rows)
        if target not in ["check", "verify"] or params:
            raise ValueError("Run check, verify or solve_linear")
        p = self.resources["problem"]
        c = self.resources["certificate"]
        x = c["candidate"]
        if len(x) != len(p["costs"]):
            raise ValueError("Enter a candidate first")
        slacks = [
            encoded(
                sum(a * v for a, v in zip(row["coefficients"], x))
                - rational(row["rhs"])
            )
            for row in p["constraints"]
        ]
        result = {
            "candidate_cost": sum(a * v for a, v in zip(p["costs"], x)),
            "constraint_slacks": slacks,
            "diagnostics": self.checks(),
            "version": self.version,
        }
        multipliers = [rational(v) for v in c["multipliers"]]
        weighted = [
            sum(
                lam * row["coefficients"][j]
                for lam, row in zip(multipliers, p["constraints"])
            )
            for j in range(len(p["costs"]))
        ]
        lower = sum(
            lam * rational(row["rhs"])
            for lam, row in zip(multipliers, p["constraints"])
        )
        result["certificate_arithmetic"] = {
            "weighted_coefficients": [encoded(v) for v in weighted],
            "coefficient_residuals": [
                encoded(v - cost) for v, cost in zip(weighted, p["costs"])
            ],
            "weighted_rhs_lower_bound": encoded(lower),
            "strict_integer_threshold": result["candidate_cost"] - 1,
            "lower_bound_above_threshold": encoded(
                lower - (result["candidate_cost"] - 1)
            ),
            "negative_multiplier_indices": [
                i for i, v in enumerate(multipliers) if v < 0
            ],
        }
        if target == "verify":
            self.artifact = copy.deepcopy(result)
            self.receipt_version = self.version
        return result
