"""Executable experiment analysis with evidence and reproducibility checks."""

import copy
import math
import statistics

from .execution import execute, language
from .scenarios import Scenario
from .program_editing import EDIT_TOOL, edit_source


class Science(Scenario):
    family = "science"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        unit_scale = self.rng.choice([1, 0.01] if split == "train" else [0.1, 0.001])
        records = []
        if level == 1:
            slope = self.rng.choice([-2, -1, 1.5, 3])
            intercept = self.rng.choice([-0.5, 0.5, 1])
            for i in range(6):
                records.append(
                    {
                        "id": i,
                        "x": i / 2,
                        "raw_y": (intercept + slope * i / 2) / unit_scale,
                        "valid": i != 2,
                    }
                )
            rule = "Fit y=intercept+slope*x to all and only valid rows, converting raw_y by unit_scale. Return effect=slope, eligible_subjects=number of included rows, hypothesis_supported=(slope>0). Fit a free intercept; do not force the line through zero."
        else:
            sites = (
                ["north", "south"] if split == "train" else ["east", "west", "central"]
            )
            for site in sites:
                for subject in range(self.rng.randint(2, 4)):
                    identifier = f"{site}-{subject}"
                    shift = self.rng.choice([-4, -2, 3, 5])
                    baseline = self.rng.randint(20, 40)
                    for phase in ["before", "after"]:
                        raw = baseline + (shift if phase == "after" else 0)
                        records.append(
                            {
                                "subject": identifier,
                                "site": site,
                                "phase": phase,
                                "raw_y": raw / unit_scale,
                                "valid": True,
                                "revision": 1,
                            }
                        )
                        if level == 3:
                            records.append(
                                {
                                    "subject": identifier,
                                    "site": site,
                                    "phase": phase,
                                    "raw_y": (raw + self.rng.randint(-2, 2))
                                    / unit_scale,
                                    "valid": subject != 0 or phase == "before",
                                    "revision": 2,
                                }
                            )
            self.rng.shuffle(records)
            rule = "For each (subject,phase), keep the highest revision BEFORE filtering valid. A subject is eligible only if both phases have a retained valid measurement. Convert raw_y by unit_scale. Compute each eligible subject's after-before difference. "
            rule += (
                "Effect is the equal-subject mean difference. "
                if level == 2
                else "Compute the mean difference within each site, then give each nonempty eligible site equal weight in effect. Do not weight sites by their subject counts. "
            )
            rule += "Return effect, eligible_subjects (total eligible subjects), and hypothesis_supported=(effect>0)."
        self.input = {
            "records": records,
            "protocol": {"unit_scale": unit_scale, "level": level},
        }
        self.resources = {
            "protocol": {
                "analysis_rule": rule,
                "unit_scale": unit_scale,
                "language": language(),
            },
            "measurements": records,
            "analysis.py": 'def compute(data):\n    return {"effect":0,"eligible_subjects":0,"hypothesis_supported":False}\n',
        }
        self.instruction = "Form and test the stated scientific hypothesis from these measurements. Read the protocol and evidence, write a reproducible pure-Python analysis, run the experiment, inspect its numerical and reproducibility diagnostics, revise and commit. The input measurements and protocol cannot be changed. Your analysis is also rerun on scaled measurements; derive results from data rather than hard-coding the original report."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {"analysis.py": EDIT_TOOL},
            "run": {
                "experiment": "params={} executes the analysis on the original and reordered measurements; returns its report and validation diagnostics"
            },
        }
        contract = 'compute(data) receives {records:the measurements rows,protocol:{unit_scale:number,level:integer}}. Read data["records"] and data["protocol"]; resource labels are not input keys.'
        self.resources["protocol"]["compute_input_contract"] = contract
        self.tools["patch"]["analysis.py"] += " " + contract

    def expected(self):
        rows, scale = self.input["records"], self.input["protocol"]["unit_scale"]
        if self.level == 1:
            valid = [r for r in rows if r["valid"]]
            xs, ys = [r["x"] for r in valid], [r["raw_y"] * scale for r in valid]
            xm, ym = statistics.mean(xs), statistics.mean(ys)
            effect = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / sum(
                (x - xm) * (x - xm) for x in xs
            )
            count = len(valid)
        else:
            latest = {}
            for r in rows:
                key = r["subject"], r["phase"]
                if key not in latest or latest[key]["revision"] < r["revision"]:
                    latest[key] = r
            differences = []
            for subject in sorted({r["subject"] for r in rows}):
                before, after = latest[subject, "before"], latest[subject, "after"]
                if before["valid"] and after["valid"]:
                    differences.append(
                        (before["site"], (after["raw_y"] - before["raw_y"]) * scale)
                    )
            count = len(differences)
            if self.level == 2:
                effect = statistics.mean(value for _, value in differences)
            else:
                effect = statistics.mean(
                    statistics.mean(value for s, value in differences if s == site)
                    for site in sorted({s for s, _ in differences})
                )
        return {
            "effect": effect,
            "eligible_subjects": count,
            "hypothesis_supported": effect > 0,
        }

    def patch(self, target, params):
        if target != "analysis.py":
            raise ValueError("Edit analysis.py only")
        source, status = edit_source(self.resources[target], params)
        self.resources[target] = source
        self.version += 1
        return {
            "analysis_updated": True,
            "version": self.version,
            "line_count": len(source.splitlines()),
            **status,
        }

    def run(self, target, params):
        if target != "experiment" or params:
            raise ValueError("Run experiment with params={}")
        other = copy.deepcopy(self.input)
        other["records"] = list(reversed(other["records"]))
        scaled = copy.deepcopy(self.input)
        for row in scaled["records"]:
            row["raw_y"] *= 2
        self.artifact = execute(
            self.resources["analysis.py"], [copy.deepcopy(self.input), other, scaled]
        )
        self.receipt_version = self.version
        return {
            "report": self.artifact.get("outputs", [None])[0]
            if "outputs" in self.artifact
            else None,
            "execution_error": self.artifact.get("error"),
            "diagnostics": self.checks(),
            "version": self.version,
        }

    def checks(self):
        outputs = (self.artifact or {}).get("outputs", [])
        wanted = self.expected()

        def matches(value, field, scale=1):
            if not isinstance(value, dict):
                return False
            actual = value.get(field)
            if field == "effect":
                return (
                    type(actual) in [int, float]
                    and math.isfinite(actual)
                    and abs(actual - wanted[field] * scale) <= 1e-6
                )
            return type(actual) is type(wanted[field]) and actual == wanted[field]

        return {
            "effect_matches_evidence": len(outputs) == 3
            and all(
                matches(o, "effect", 2 if i == 2 else 1) for i, o in enumerate(outputs)
            ),
            "cohort_matches_protocol": len(outputs) == 3
            and all(matches(o, "eligible_subjects") for o in outputs),
            "hypothesis_reproducible": len(outputs) == 3
            and all(matches(o, "hypothesis_supported") for o in outputs),
        }
