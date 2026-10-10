"""Private software scheduling redesign, outside the frozen eight-domain run."""

from itertools import combinations
from .scenarios import Scenario
from .program_editing import EDIT_TOOL, edit_source
from .code_tasks import Software
import copy
from .execution import language, execute


class CodeScheduling(Software):
    def __init__(self, seed, level, split="train"):
        Scenario.__init__(self, seed, level, split)
        self.inputs = [self.example(i) for i in range(10)]
        contract = "Repair deterministic batching in a build service. Return {waves:[[sorted job IDs],...],blocked:[sorted remaining IDs]}. Remove initially completed and cancelled IDs from pending; completed IDs satisfy dependencies, cancelled IDs do not. At each wave, ready jobs require all IDs in needs to be completed AND at least one completed ID from each group in any_of. Evaluate readiness only before selecting the whole wave. Among all nonempty ready subsets respecting total cpu <= capacity.cpu, total memory <= capacity.memory, and at most one job with each nonempty exclusive tag, choose maximum total value, then minimum total cpu, then lexicographically smallest sorted ID list. Add all selected jobs to completed together after the whole wave, then repeat. If no nonempty feasible ready subset exists, stop and list all remaining jobs as blocked. Input order is irrelevant; capacities apply afresh per wave. This is subset optimization, not greedy priority scheduling."
        source = 'def compute(data):\n    done = set(data["completed"])\n    waves = []\n    blocked = []\n    for job in sorted(data["jobs"],key=lambda j:-j["value"]):\n        if all(dep in done for dep in job["needs"]) and job["cpu"] <= data["capacity"]["cpu"]:\n            waves.append([job["id"]])\n            done.add(job["id"])\n        else:\n            blocked.append(job["id"])\n    return {"waves":waves,"blocked":sorted(blocked)}\n'
        self.resources = {
            "README": {
                "goal": contract,
                "entrypoint": "src/repair.py",
                "language": language(),
            },
            "src/repair.py": source,
            "tests": self.inputs[:2],
        }
        self.instruction = "Fix a failing behavior in this build-service repository. Inspect the contract, source and public cases, reproduce the defect, repair compute(data), execute the regression suite and inspect its outputs before committing. A greedy patch is insufficient for resource-constrained batching."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {"src/repair.py": EDIT_TOOL},
            "run": {
                "tests": "params={} executes Python on public and additional contract cases; returns public outputs and aggregate pass count"
            },
        }

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
        passed = [o == self.expected(d) for o, d in zip(result["outputs"], self.inputs)]
        return {
            "public_outputs": result["outputs"][:2],
            "public_expected": [self.expected(x) for x in self.inputs[:2]],
            "passed": sum(passed),
            "total": len(passed),
            "version": self.version,
        }

    def example(self, index):
        rng = self.rng
        count = 6 + self.level + (2 if self.split == "holdout" else 0)
        jobs = []
        for i in range(count):
            needs = []
            if self.level >= 2 and i >= 3 and index % 3 != 0:
                needs = rng.sample(["j" + str(n) for n in range(i)], rng.choice([1, 2]))
            any_of = []
            if self.level == 3 and i >= 4 and index % 2:
                any_of = [["external", "j" + str(rng.randrange(i))]]
            jobs.append(
                {
                    "id": "j" + str(i),
                    "needs": needs,
                    "any_of": any_of,
                    "cpu": rng.randint(1, 5),
                    "memory": rng.randint(1, 6) if self.level >= 2 else 1,
                    "value": rng.randint(1, 12),
                    "exclusive": rng.choice(["", "", "deviceA", "deviceB"])
                    if self.level == 3
                    else "",
                }
            )
        if self.level >= 2 and index % 4 == 1:
            jobs[-1]["needs"] = [jobs[-2]["id"]]
            jobs[-2]["needs"] = [jobs[-1]["id"]]
        if self.level == 3 and index % 4 == 2:
            jobs[-1]["any_of"] = [["missing", jobs[-1]["id"]]]
        cancelled = [jobs[1]["id"]] if self.level == 3 and index % 3 == 1 else []
        completed = ["external"] if index % 2 else []
        if self.level == 3 and index % 5 == 3:
            completed.append(jobs[0]["id"])
        rng.shuffle(jobs)
        return {
            "jobs": jobs,
            "capacity": {
                "cpu": rng.randint(5, 8),
                "memory": rng.randint(6, 10) if self.level >= 2 else count + 1,
            },
            "completed": completed,
            "cancelled": cancelled,
        }

    def expected(self, data):
        completed = set(data["completed"])
        pending = {
            r["id"]: r
            for r in data["jobs"]
            if r["id"] not in completed | set(data["cancelled"])
        }
        waves = []
        while pending:
            ready = sorted(
                job
                for job, r in pending.items()
                if set(r["needs"]) <= completed
                and all(set(group) & completed for group in r["any_of"])
            )
            feasible = []
            for count in range(1, len(ready) + 1):
                for subset in combinations(ready, count):
                    rows = [pending[j] for j in subset]
                    tags = [r["exclusive"] for r in rows if r["exclusive"]]
                    cpu = sum(r["cpu"] for r in rows)
                    if (
                        cpu <= data["capacity"]["cpu"]
                        and sum(r["memory"] for r in rows) <= data["capacity"]["memory"]
                        and len(tags) == len(set(tags))
                    ):
                        feasible.append((-sum(r["value"] for r in rows), cpu, subset))
            if not feasible:
                break
            selected = min(feasible)[2]
            waves.append(list(selected))
            completed.update(selected)
            for job in selected:
                del pending[job]
        return {"waves": waves, "blocked": sorted(pending)}
