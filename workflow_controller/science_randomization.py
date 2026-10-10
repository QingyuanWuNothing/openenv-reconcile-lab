"""Private experimental redesign: executable exact randomization tests."""

import copy
from itertools import combinations, product
import math
import statistics
from .scenarios import Scenario
from .program_editing import EDIT_TOOL, edit_source
from .science_tasks import Science
from .execution import execute, language


class ScienceRandomization(Science):
    def __init__(self, seed, level, split="train"):
        Scenario.__init__(self, seed, level, split)
        sites = (
            ["north"]
            if level == 1
            else (
                ["east", "west", "central"]
                if split == "holdout"
                else ["north", "south"]
            )
        )
        records, roster = [], []
        for site_index, site in enumerate(sites):
            per_arm = 3 if level == 1 else 2
            for arm in ["T", "C"]:
                for index in range(per_arm):
                    subject = f"{site}-{arm}-{index}"
                    consent = not (
                        level == 3 and site_index == 0 and arm == "T" and index == 0
                    )
                    roster.append(
                        {
                            "subject": subject,
                            "site": site,
                            "arm": arm,
                            "consent": consent,
                            "revision": 1,
                            "tick": 1,
                        }
                    )
                    if level == 3:
                        roster.append(
                            {
                                "subject": subject,
                                "site": site,
                                "arm": arm,
                                "consent": False,
                                "revision": 2,
                                "tick": 9,
                            }
                        )
                    baseline = self.rng.randint(20, 40)
                    delta = self.rng.randint(-3, 3) + (
                        self.rng.choice([-2, 2, 4]) if arm == "T" else 0
                    )
                    for phase, value in [
                        ("before", baseline),
                        ("after", baseline + delta),
                    ]:
                        unit = self.rng.choice(
                            ["base", "centi"] if split == "train" else ["deci", "milli"]
                        )
                        scale = {"base": 1, "centi": 0.01, "deci": 0.1, "milli": 0.001}[
                            unit
                        ]
                        records.append(
                            {
                                "subject": subject,
                                "phase": phase,
                                "raw_y": value / scale,
                                "unit": unit,
                                "valid": True,
                                "revision": 1,
                                "tick": 1,
                            }
                        )
                        if level == 3:
                            records.append(
                                {
                                    "subject": subject,
                                    "phase": phase,
                                    "raw_y": (value + self.rng.randint(-2, 2)) / scale,
                                    "unit": unit,
                                    "valid": True,
                                    "revision": 2,
                                    "tick": 4,
                                }
                            )
                            if index == 0:
                                records.append(
                                    {
                                        "subject": subject,
                                        "phase": phase,
                                        "raw_y": 999 / scale,
                                        "unit": unit,
                                        "valid": False,
                                        "revision": 3,
                                        "tick": 9,
                                    }
                                )
        self.rng.shuffle(records)
        self.rng.shuffle(roster)
        weights = {site: 1 if level < 3 else 1 + 2 * i for i, site in enumerate(sites)}
        protocol = {
            "cutoff": 5,
            "unit_scales": {"base": 1, "centi": 0.01, "deci": 0.1, "milli": 0.001},
            "site_weights": weights,
            "alternative": self.rng.choice(["greater", "two_sided"]),
            "alpha": 0.1,
            "positive_effect_threshold": 1e-6,
            "comparison_tolerance": 1e-9,
        }
        rule = "Execute an exact randomization test of whether treatment improves the before-to-after change. First discard records AND roster revisions with tick>cutoff. For each subject's roster entry and each (subject,phase) measurement, choose the highest revision before filtering consent/valid. Eligible subjects need consenting roster and valid retained before AND after measurements. Convert each measurement by its own unit scale before differencing. For every site containing eligible T and C subjects, compute mean(T change)-mean(C change); effect is the site_weights-weighted mean of these site contrasts, normalizing by the sum of participating site weights. Use these same eligible subjects for an exact null distribution: enumerate all distinct assignments that preserve each site's observed number of T subjects (exchange labels only within sites). Every assignment has equal probability; re-evaluate the same weighted contrast for each. For greater, p_value is the fraction with statistic >= observed effect - comparison_tolerance. For two_sided, compare absolute statistics instead. Include ties and the observed assignment. Return effect, p_value, eligible_subjects (count), included_subject_ids (sorted IDs), and hypothesis_supported=(effect>positive_effect_threshold AND p_value<=alpha). Reordering either source must not change the result. The analysis is also executed on controlled measurement scaling and consent changes; derive every output from data instead of hard-coding the observed report. Do not pool sites, use unrestricted global label shuffling, compute a Gaussian approximation, or confuse p_value with the effect."
        self.input = {"records": records, "roster": roster, "protocol": protocol}
        self.resources = {
            "protocol": {"analysis_rule": rule, **protocol, "language": language()},
            "measurements": records,
            "roster": roster,
            "analysis.py": 'def compute(data):\n    return {"effect":0,"p_value":1,"eligible_subjects":0,"included_subject_ids":[],"hypothesis_supported":False}\n',
        }
        self.instruction = "Form and test the scientific hypothesis using an executable, reproducible exact randomization analysis. Inspect protocol, measurements and roster, implement compute(data), run experiment, inspect diagnostics, revise if needed and commit."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {"analysis.py": EDIT_TOOL},
            "run": {
                "experiment": "params={} executes the analysis on original and reordered evidence sources, with numerical/cohort/randomization diagnostics"
            },
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

    def cohorts(self, data=None):
        data = self.input if data is None else data
        cutoff = data["protocol"]["cutoff"]
        roster = {}
        measurements = {}
        for r in data["roster"]:
            if r["tick"] <= cutoff and (
                r["subject"] not in roster
                or roster[r["subject"]]["revision"] < r["revision"]
            ):
                roster[r["subject"]] = r
        for r in data["records"]:
            key = (r["subject"], r["phase"])
            if r["tick"] <= cutoff and (
                key not in measurements or measurements[key]["revision"] < r["revision"]
            ):
                measurements[key] = r
        changes = {}
        for subject, person in roster.items():
            before, after = (
                measurements.get((subject, "before")),
                measurements.get((subject, "after")),
            )
            if (
                person["consent"]
                and before
                and after
                and before["valid"]
                and after["valid"]
            ):
                scales = data["protocol"]["unit_scales"]
                changes[subject] = (
                    after["raw_y"] * scales[after["unit"]]
                    - before["raw_y"] * scales[before["unit"]]
                )
        return roster, changes

    def expected(self, data=None):
        data = self.input if data is None else data
        roster, changes = self.cohorts(data)
        protocol = data["protocol"]
        sites = sorted({roster[k]["site"] for k in changes})
        pools = {s: sorted(k for k in changes if roster[k]["site"] == s) for s in sites}
        observed = {k for k in changes if roster[k]["arm"] == "T"}
        counts = {s: len(observed & set(pools[s])) for s in sites}
        sites = [s for s in sites if 0 < counts[s] < len(pools[s])]

        def statistic(treatment):
            return sum(
                protocol["site_weights"][site]
                * (
                    statistics.mean(changes[k] for k in pools[site] if k in treatment)
                    - statistics.mean(
                        changes[k] for k in pools[site] if k not in treatment
                    )
                )
                for site in sites
            ) / sum(protocol["site_weights"][s] for s in sites)

        effect = statistic(observed)
        total = tail = 0
        for assignment in product(
            *(list(combinations(pools[s], counts[s])) for s in sites)
        ):
            value = statistic(set().union(*(set(a) for a in assignment)))
            left, right = (
                (abs(value), abs(effect))
                if protocol["alternative"] == "two_sided"
                else (value, effect)
            )
            total += 1
            tail += left >= right - protocol["comparison_tolerance"]
        p = tail / total
        return {
            "effect": effect,
            "p_value": p,
            "eligible_subjects": len(changes),
            "included_subject_ids": sorted(changes),
            "hypothesis_supported": effect > protocol["positive_effect_threshold"]
            and p <= protocol["alpha"],
        }

    def variants(self):
        original = copy.deepcopy(self.input)
        reordered = copy.deepcopy(self.input)
        reordered["records"].reverse()
        reordered["roster"].reverse()
        scaled = copy.deepcopy(self.input)
        for row in scaled["records"]:
            row["raw_y"] *= 2
        changed = copy.deepcopy(self.input)
        roster, cohort = self.cohorts()
        control = next(k for k in sorted(cohort) if roster[k]["arm"] == "C")
        for row in changed["roster"]:
            if row["subject"] == control:
                row["consent"] = False
        return [original, reordered, scaled, changed]

    def run(self, target, params):
        if target != "experiment" or params:
            raise ValueError("Run experiment with params={}")
        self.artifact = execute(self.resources["analysis.py"], self.variants())
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
        wanted = [self.expected(data) for data in self.variants()]

        def matches(row, expected, key):
            if not isinstance(row, dict):
                return False
            value = row.get(key)
            if key in ["effect", "p_value"]:
                return (
                    type(value) in [int, float]
                    and math.isfinite(value)
                    and abs(value - expected[key]) <= 1e-6
                )
            return type(value) is type(expected[key]) and value == expected[key]

        return {
            "effect_matches_evidence": len(outputs) == len(wanted)
            and all(matches(o, w, "effect") for o, w in zip(outputs, wanted)),
            "cohort_matches_protocol": len(outputs) == len(wanted)
            and all(
                matches(o, w, "eligible_subjects")
                and matches(o, w, "included_subject_ids")
                for o, w in zip(outputs, wanted)
            ),
            "randomization_and_hypothesis_reproducible": len(outputs) == len(wanted)
            and all(
                matches(o, w, "p_value") and matches(o, w, "hypothesis_supported")
                for o, w in zip(outputs, wanted)
            ),
        }
