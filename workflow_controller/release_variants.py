"""Production tools that reduce rollout cost without supplying task solutions."""

import math
from .science_kinetics import ScienceKinetics
from .math_basis import MathBasis
from .media_cut import MediaCut, nearest_frame
from fractions import Fraction


class ScienceEfficient(ScienceKinetics):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        self.tools["run"].update(
            {
                "measure_batch": "params={conditions:[{substrate,inhibitor,unit},...],replicates:2..5}; execute 1–6 agent-chosen assays in order. Each is a separate recorded measurement run; consumes the normal 12-run limit. No conditions are chosen for you.",
                "compare_models": "params={models:[{mechanism,hill},...]}; fit 1–8 distinct agent-selected models to the actual notebook. Compare observed signal residuals; does not choose a model, write the hypothesis or disclose simulation parameters.",
            }
        )

    def run(self, target, params):
        if target == "compare_models":
            models = params.get("models")
            if (
                set(params) != {"models"}
                or not isinstance(models, list)
                or not 1 <= len(models) <= 8
                or any(
                    not isinstance(m, dict) or set(m) != {"mechanism", "hill"}
                    for m in models
                )
            ):
                raise ValueError("Supply 1–8 declared model/exponent pairs")
            protocol = self.resources["protocol"]
            if any(
                m["mechanism"] not in protocol["mechanisms"]
                or type(m["hill"]) is not int
                or m["hill"] not in protocol["candidate_hill"]
                for m in models
            ) or len({(m["mechanism"], m["hill"]) for m in models}) != len(models):
                raise ValueError("Use distinct declared model/exponent pairs")
            return {
                "fits": [super(ScienceEfficient, self).run("fit", m) for m in models],
                "note": "Measured evidence only. Choose a hypothesis, check its fit, and commit after reproducing the required experiment.",
            }
        if target == "measure_batch":
            conditions = params.get("conditions")
            replicates = params.get("replicates")
            if (
                set(params) != {"conditions", "replicates"}
                or not isinstance(conditions, list)
                or not 1 <= len(conditions) <= 6
                or type(replicates) is not int
                or not 2 <= replicates <= 5
            ):
                raise ValueError("Supply 1–6 assay conditions and 2–5 replicates")
            for c in conditions:
                if (
                    not isinstance(c, dict)
                    or set(c) != {"substrate", "inhibitor", "unit"}
                    or c["unit"] not in self.resources["protocol"]["unit_to_mM"]
                    or any(
                        type(c[k]) not in [int, float]
                        or not math.isfinite(c[k])
                        or not 0 <= c[k] <= 100000
                        for k in ["substrate", "inhibitor"]
                    )
                ):
                    raise ValueError(
                        "Use the declared finite nonnegative assay parameters"
                    )
            if len(self.resources["notebook"]) + len(conditions) > 12:
                raise ValueError(
                    "Assay run budget exhausted; no batch measurements taken"
                )
            readings = [
                super(ScienceEfficient, self).run(
                    "assay", {**c, "replicates": replicates}
                )
                for c in conditions
            ]
            return {
                "measurements": readings,
                "remaining_assay_runs": 12 - len(self.resources["notebook"]),
            }
        return super().run(target, params)


class MathBridge(MathBasis):
    def __init__(self, seed, level, split="train"):
        super().__init__(
            seed, level, split, variables=2 if level == 2 else 3, dense=True
        )


class MediaBridge(MediaCut):
    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        count = (1 if level == 2 else 2) + (split == "holdout")
        self.resources["edit_list"] = self.resources["edit_list"][:count]
        self.tools["run"]["retime"] = (
            "params={id:cut ID,source_frame:integer}; map this agent-selected source boundary through the assembled timeline using exact round-half-up. Does not select words or write captions. Assemble first."
        )

    def run(self, target, params):
        if target == "preview_cut":
            result = super().run(target, params)
            result["word_cards"] = [
                w for w in result["word_cards"] if w["selection"] != "outside"
            ]
            result["note"] = (
                "Chronological words overlapping the selected source clip. Retain full words only; partial words must be dropped. Retime your chosen first/last word boundary, edit a caption, inspect the actual export and commit."
            )
            return result
        if target == "retime":
            if (
                set(params) != {"id", "source_frame"}
                or type(params["source_frame"]) is not int
            ):
                raise ValueError("Provide a cut ID and integer source frame")
            cut = next(
                (e for e in self.resources["edit_list"] if e["id"] == params["id"]),
                None,
            )
            timeline = next(
                (t for t in self.resources["timeline"] if t["id"] == params["id"]), None
            )
            if cut is None or timeline is None:
                raise ValueError("Choose an existing cut and run assemble first")
            if not cut["in_frame"] <= params["source_frame"] <= cut["out_frame"]:
                raise ValueError("Choose a source boundary within the cut")
            ratio = Fraction(
                timeline["retiming_ratio"]["num"], timeline["retiming_ratio"]["den"]
            )
            return {
                "id": params["id"],
                "source_frame": params["source_frame"],
                "delivery_frame": timeline["delivery_start_frame"]
                + nearest_frame((params["source_frame"] - cut["in_frame"]) * ratio),
            }
        return super().run(target, params)
