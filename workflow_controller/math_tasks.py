"""Exact row-operation proofs for unique, inconsistent and rank-deficient systems."""

import copy
from fractions import Fraction
import math

from .scenarios import Scenario


def rational(value):
    if type(value) in [int, float] and math.isfinite(value):
        result = Fraction(str(value))
    elif (
        isinstance(value, dict)
        and set(value) == {"num", "den"}
        and type(value["num"]) is int
        and type(value["den"]) is int
        and value["den"] != 0
    ):
        result = Fraction(value["num"], value["den"])
    else:
        raise ValueError("Use a finite number or {num:integer,den:nonzero integer}")
    if abs(result.numerator) > 10**9 or result.denominator > 10**9:
        raise ValueError("Rational value exceeds arithmetic limits")
    return result


def encoded(value):
    return (
        value.numerator
        if value.denominator == 1
        else {"num": value.numerator, "den": value.denominator}
    )


class Mathematics(Scenario):
    family = "math"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.size = 2 if level == 1 else 3
        rows = [
            [Fraction(int(i == j)) for j in range(self.size)] for i in range(self.size)
        ]
        for _ in range(2 + level):
            target, source = self.rng.sample(range(self.size), 2)
            factor = self.rng.choice([-2, -1, 1, 2])
            rows[target] = [a + factor * b for a, b in zip(rows[target], rows[source])]
        solution = [self.rng.randint(-3, 4) for _ in rows]
        augmented = [row + [sum(a * x for a, x in zip(row, solution))] for row in rows]
        if level == 3:
            augmented[-1] = list(augmented[0])
            if self.rng.choice([True, False]):
                augmented[-1][-1] += 1
        if split == "holdout" or level == 3:
            for i, row in enumerate(augmented):
                factor = Fraction(1, i + 2)
                augmented[i] = [x * factor for x in row]
        self.rng.shuffle(augmented)
        self.original = copy.deepcopy(augmented)
        self.rows = copy.deepcopy(augmented)
        self.conclusion = {"classification": "unknown", "solution": []}
        self.resources = {
            "problem": {
                "variables": [f"x{i + 1}" for i in range(self.size)],
                "augmented_matrix": self.view(),
                "goal": "Classify the system as unique, underdetermined or inconsistent. Produce an exact reduced-row-echelon proof using elementary row operations. For consistent systems also supply one solution vector satisfying the ORIGINAL equations; free variables may be assigned any valid values. For inconsistent systems use an empty solution. A numerical guess without a reduced proof is insufficient.",
                "numbers": "Integers or exact {num,den} objects; row indexes start at 0. Absolute numerator and positive denominator must each be <=1000000000.",
            },
            "matrix": self.view(),
            "conclusion": copy.deepcopy(self.conclusion),
        }
        self.instruction = "Work through this linear-system problem, check uniqueness/consistency assumptions and validate the conclusion with executable exact-arithmetic row operations. Inspect the evolving matrix, revise operations, enter a conclusion and run verify before committing the proof."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "conclusion": "params={classification:'unique'|'underdetermined'|'inconsistent',solution:[number or {num,den},...]}; replace the conclusion"
            },
            "run": {
                "rowop": "params={kind:'swap'|'scale'|'add',target:row,source?:row,factor?:number or {num,den}}; swap target/source, scale target by nonzero factor, or add factor*source to target",
                "verify": "params={} tests reduced proof, classification and original-equation residuals",
            },
        }

    def view(self):
        return [[encoded(x) for x in row] for row in self.rows]

    def patch(self, target, params):
        if (
            target != "conclusion"
            or set(params) != {"classification", "solution"}
            or params["classification"]
            not in ["unique", "underdetermined", "inconsistent"]
            or not isinstance(params["solution"], list)
            or len(params["solution"]) not in [0, self.size]
        ):
            raise ValueError("Provide a complete classification and solution vector")
        values = [rational(x) for x in params["solution"]]
        self.conclusion = {
            "classification": params["classification"],
            "solution": [encoded(x) for x in values],
        }
        self.resources["conclusion"] = copy.deepcopy(self.conclusion)
        self.version += 1
        return {"conclusion": copy.deepcopy(self.conclusion), "version": self.version}

    def run(self, target, params):
        if target == "rowop":
            if set(params) - {"kind", "target", "source", "factor"} or params.get(
                "kind"
            ) not in ["swap", "scale", "add"]:
                raise ValueError("Unknown row operation")
            t, s = params.get("target"), params.get("source")
            if type(t) is not int or not 0 <= t < len(self.rows):
                raise ValueError("Invalid target row")
            updated = copy.deepcopy(self.rows)
            if params["kind"] == "scale":
                factor = rational(params.get("factor"))
                if not factor:
                    raise ValueError("Scaling by zero destroys equation equivalence")
                updated[t] = [x * factor for x in updated[t]]
            else:
                if type(s) is not int or not 0 <= s < len(self.rows) or s == t:
                    raise ValueError("Use a distinct valid source row")
                if params["kind"] == "swap":
                    updated[t], updated[s] = updated[s], updated[t]
                else:
                    factor = rational(params.get("factor"))
                    updated[t] = [
                        a + factor * b for a, b in zip(updated[t], updated[s])
                    ]
            for row in updated:
                for x in row:
                    rational(encoded(x))
            self.rows = updated
            self.resources["matrix"] = self.view()
            self.version += 1
            return {"matrix": self.view(), "version": self.version}
        if target != "verify" or params:
            raise ValueError("Run rowop or verify")
        self.artifact = {
            "matrix": copy.deepcopy(self.rows),
            "conclusion": copy.deepcopy(self.conclusion),
        }
        self.receipt_version = self.version
        values = [rational(x) for x in self.conclusion["solution"]]
        residuals = (
            [
                encoded(sum(a * x for a, x in zip(row[:-1], values)) - row[-1])
                for row in self.original
            ]
            if len(values) == self.size
            else []
        )
        return {
            "diagnostics": self.checks(),
            "original_residuals": residuals,
            "version": self.version,
        }

    def checks(self):
        pivots = []
        reduced = True
        zero_seen = False
        for i, row in enumerate(self.rows):
            nonzero = next((j for j, x in enumerate(row) if x), None)
            if nonzero is None:
                zero_seen = True
                continue
            reduced &= (
                not zero_seen
                and row[nonzero] == 1
                and (not pivots or pivots[-1][1] < nonzero)
            )
            reduced &= all(
                k == i or other[nonzero] == 0 for k, other in enumerate(self.rows)
            )
            pivots.append((i, nonzero))
        contradiction = any(
            all(x == 0 for x in row[:-1]) and row[-1] != 0 for row in self.rows
        )
        rank = sum(any(x != 0 for x in row[:-1]) for row in self.rows)
        kind = (
            "inconsistent"
            if contradiction
            else "unique"
            if rank == self.size
            else "underdetermined"
        )
        values = [rational(x) for x in self.conclusion["solution"]]
        witness = (
            not values
            if kind == "inconsistent"
            else len(values) == self.size
            and all(
                sum(a * x for a, x in zip(row[:-1], values)) == row[-1]
                for row in self.original
            )
        )
        return {
            "exact_reduced_proof": bool(reduced),
            "classification_supported": bool(
                reduced and self.conclusion["classification"] == kind
            ),
            "original_equations_verified": bool(witness),
        }
