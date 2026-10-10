"""Private deeper proof workflows with atomic batched row operations."""

import copy
from fractions import Fraction
from .math_tasks import Mathematics


class MathDense(Mathematics):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.size = 3 + level
        rows = [
            [Fraction(self.rng.randint(-2, 2)) for _ in range(self.size)]
            for _ in range(self.size)
        ]
        for i, row in enumerate(rows):
            row[i] = sum(
                abs(x) for j, x in enumerate(row) if i != j
            ) + self.rng.randint(1, 3)
        solution = [self.rng.randint(-3, 4) for _ in rows]
        augmented = [row + [sum(a * x for a, x in zip(row, solution))] for row in rows]
        if level == 3:
            augmented[-2] = list(augmented[0])
            augmented[-1] = [a + b for a, b in zip(augmented[0], augmented[1])]
            if self.rng.choice([True, False]):
                augmented[-1][-1] += 1
        if split == "holdout":
            for i, row in enumerate(augmented):
                augmented[i] = [x * Fraction(1, i + 2) for x in row]
        self.rng.shuffle(augmented)
        self.original = copy.deepcopy(augmented)
        self.rows = copy.deepcopy(augmented)
        self.resources["problem"]["variables"] = [f"x{i + 1}" for i in range(self.size)]
        self.resources["problem"]["augmented_matrix"] = self.view()
        self.resources["matrix"] = self.view()
        self.instruction += " Use run target rowops to batch up to six elementary operations per action; inspect the returned matrix and adapt the next batch. Batching permits a complete proof within 32 actions. Operations are exact and applied sequentially; an invalid batch leaves the matrix unchanged."
        self.tools["run"]["rowops"] = (
            "params={operations:[{kind,target,source?,factor?},...]}; 1–6 ordinary rowop parameter objects, applied sequentially and atomically; returns the final matrix"
        )

    def run(self, target, params):
        if target != "rowops":
            return super().run(target, params)
        operations = params.get("operations")
        if (
            set(params) != {"operations"}
            or not isinstance(operations, list)
            or not 1 <= len(operations) <= 6
            or any(not isinstance(op, dict) for op in operations)
        ):
            raise ValueError("Provide 1–6 row operations")
        rows, version = copy.deepcopy(self.rows), self.version
        try:
            for op in operations:
                result = super().run("rowop", op)
        except (ValueError, TypeError, KeyError, OverflowError):
            self.rows = rows
            self.version = version
            self.resources["matrix"] = self.view()
            raise
        return result
