"""Repository repair tasks with actual execution and independent regression checks."""

import copy

from .execution import execute, language
from .scenarios import Scenario
from .program_editing import EDIT_TOOL, edit_source


class Software(Scenario):
    family = "code"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.kind = ["inventory", "intervals", "dependencies"][level - 1]
        if self.kind == "inventory":
            contract = "Aggregate integer quantity by SKU after stripping surrounding whitespace and lowercasing. Preserve negative adjustments and zero totals. Return a dictionary keyed by normalized SKU."
            source = 'def compute(data):\n    totals = {}\n    for r in data["records"]:\n        totals[r["sku"].lower()] = r["quantity"]\n    return totals\n'
        elif self.kind == "intervals":
            contract = "Return sorted merged intervals as [[start,end],...]. Inputs have start<end and may be unsorted/nested. Overlaps always merge; touching boundaries merge exactly when merge_touching=true. Preserve the furthest end of nested intervals."
            source = 'def compute(data):\n    result = []\n    for start,end in data["intervals"]:\n        if result and start < result[-1][0]:\n            result[-1][1] = end\n        else:\n            result.append([start,end])\n    return result\n'
        else:
            contract = "Return {waves:[[sorted task IDs],...],blocked:[sorted task IDs]}. At each wave, all currently uncompleted tasks whose unique prerequisites are already completed enter together; only after the whole wave is selected do they become completed. Honor data.completed external prerequisites. Missing prerequisites and cycles block affected tasks. Empty waves are omitted. Task order and duplicate prerequisites must not affect output."
            source = 'def compute(data):\n    done = set(data["completed"])\n    waves = []\n    blocked = []\n    for r in data["tasks"]:\n        if all(x in done for x in r["needs"]):\n            waves.append([r["id"]])\n            done.add(r["id"])\n        else:\n            blocked.append(r["id"])\n    return {"waves":waves,"blocked":blocked}\n'
        self.inputs = [self.example(i) for i in range(10)]
        self.resources = {
            "README": {
                "goal": contract,
                "entrypoint": "src/repair.py",
                "language": language(),
            },
            "src/repair.py": source,
            "tests": self.inputs[:2],
        }
        self.instruction = "Inspect this small repository, reproduce its failing behavior, repair the Python function, run regression tests, inspect results and commit the tested source. Several implementations are valid. Hidden cases follow the same public contract; public test outputs and aggregate diagnostics are available."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {"src/repair.py": EDIT_TOOL},
            "run": {
                "tests": "params={} executes Python on public and additional contract cases; returns public outputs and total pass count"
            },
        }

    def example(self, index):
        rng = self.rng
        if self.kind == "inventory":
            skus = (
                ["bolt", "nut", "washer"]
                if self.split == "train"
                else ["gear", "pin", "seal", "shaft"]
            )
            records = [
                {
                    "sku": rng.choice(skus).upper()
                    if j % 2
                    else " " + rng.choice(skus) + " ",
                    "quantity": rng.randint(-4, 9),
                }
                for j in range(6 + index % 4)
            ]
            return {"records": records}
        if self.kind == "intervals":
            intervals = [[1, 4], [2, 3], [4, 6], [8, 9]]
            shift = rng.randint(0, 20)
            intervals = [[a + shift, b + shift] for a, b in intervals]
            if self.split == "holdout":
                intervals += [[shift, shift + 7], [shift + 9, shift + 12]]
            rng.shuffle(intervals)
            return {"intervals": intervals, "merge_touching": bool(index % 2)}
        tasks = [
            {"id": "a", "needs": []},
            {"id": "b", "needs": []},
            {"id": "c", "needs": ["a", "b", "a"]},
            {"id": "d", "needs": ["c"]},
            {"id": "e", "needs": ["external"]},
        ]
        if index % 2:
            tasks += [{"id": "x", "needs": ["y"]}, {"id": "y", "needs": ["x"]}]
        if self.split == "holdout":
            tasks += [
                {"id": "f", "needs": ["d", "e"]},
                {"id": "g", "needs": ["missing"]},
            ]
        rng.shuffle(tasks)
        return {"tasks": tasks, "completed": ["external"] if index % 3 else []}

    def expected(self, data):
        if self.kind == "inventory":
            result = {}
            for r in data["records"]:
                key = r["sku"].strip().lower()
                result[key] = result.get(key, 0) + r["quantity"]
            return result
        if self.kind == "intervals":
            result = []
            for start, end in sorted(data["intervals"]):
                join = bool(result) and (
                    start < result[-1][1]
                    or data["merge_touching"]
                    and start == result[-1][1]
                )
                if join:
                    result[-1][1] = max(result[-1][1], end)
                else:
                    result.append([start, end])
            return result
        done, waiting = (
            set(data["completed"]),
            {
                r["id"]: set(r["needs"])
                for r in data["tasks"]
                if r["id"] not in data["completed"]
            },
        )
        waves = []
        while waiting:
            ready = sorted(k for k, needs in waiting.items() if needs <= done)
            if not ready:
                break
            waves.append(ready)
            done.update(ready)
            for k in ready:
                del waiting[k]
        return {"waves": waves, "blocked": sorted(waiting)}

    def patch(self, target, params):
        if target != "src/repair.py":
            raise ValueError("Edit src/repair.py only")
        source, status = edit_source(self.resources[target], params)
        self.resources[target] = source
        self.version += 1
        return {
            "source_updated": True,
            "version": self.version,
            "line_count": len(source.splitlines()),
            **status,
        }

    def run(self, target, params):
        if target != "tests" or params:
            raise ValueError("Run tests with params={}")
        result = execute(self.resources["src/repair.py"], copy.deepcopy(self.inputs))
        self.artifact = result
        self.receipt_version = self.version
        if "error" in result:
            return result
        passed = [
            output == self.expected(data)
            for output, data in zip(result["outputs"], self.inputs)
        ]
        return {
            "public_outputs": result["outputs"][:2],
            "public_expected": [self.expected(x) for x in self.inputs[:2]],
            "passed": sum(passed),
            "total": len(passed),
            "version": self.version,
        }

    def checks(self):
        outputs = (self.artifact or {}).get("outputs", [])
        return {
            "regression_behavior": len(outputs) == len(self.inputs)
            and all(o == self.expected(d) for o, d in zip(outputs, self.inputs)),
            "python_executed": len(outputs) == len(self.inputs),
            "source_repaired": self.version > 0,
        }
