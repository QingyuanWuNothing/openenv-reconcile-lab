"""A standard exact basis solver for agent-selected public inequalities."""

from .math_dual import MathDual, solve


class MathBasis(MathDual):
    def __init__(self, seed, level, split="train", **kwargs):
        super().__init__(seed, level, split, **kwargs)
        self.tools["run"]["basis"] = (
            "params={constraint_ids:[IDs]}; select exactly as many public inequalities as variables. Solve their equalities and the corresponding transpose system for objective multipliers. Does not choose constraints, round an integer candidate, check other inequalities, write a certificate or prove optimality."
        )
        self.instruction += " You may run basis with your selected constraint IDs instead of manually transcribing two augmented matrices. Its primal solution is continuous: you still need an integer feasible candidate, zero weights for unused rows, and a checked lower bound. Use run check to diagnose a proposed proof and revise it."

    def run(self, target, params):
        if target != "basis":
            return super().run(target, params)
        p = self.resources["problem"]
        ids = params.get("constraint_ids")
        n = len(p["costs"])
        by_id = {row["id"]: row for row in p["constraints"]}
        if (
            set(params) != {"constraint_ids"}
            or not isinstance(ids, list)
            or len(ids) != n
            or any(not isinstance(i, str) or i not in by_id for i in ids)
            or len(set(ids)) != n
        ):
            raise ValueError("Choose one distinct public constraint ID per variable")
        rows = [by_id[i] for i in ids]
        primal = solve([row["coefficients"] + [row["rhs"]] for row in rows])
        dual = solve(
            [
                [row["coefficients"][j] for row in rows] + [cost]
                for j, cost in enumerate(p["costs"])
            ]
        )
        return {
            "selected_constraints": ids,
            "continuous_point": primal,
            "selected_multipliers": dual,
            "note": "Equality systems for your selection only. A continuous point may violate other inequalities or integrality. Selected multipliers may be negative or provide an insufficient integer bound. Build and check your own complete certificate in published constraint order.",
        }
