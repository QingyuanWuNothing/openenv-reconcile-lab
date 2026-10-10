"""Private active-science redesign: calibrated experiments and model identification."""

import copy
import math
from fractions import Fraction
from itertools import product
from .scenarios import Scenario
from .numeric_tools import calculate


MECHANISMS = ["competitive", "noncompetitive", "uncompetitive", "mixed"]
FIELDS = {
    "mechanism",
    "vmax",
    "km",
    "ki_free",
    "ki_bound",
    "signal_gain",
    "signal_offset",
    "hill",
}


def activity(report, substrate, inhibitor):
    free = 1 + inhibitor / report["ki_free"] if report["ki_free"] is not None else 1
    bound = 1 + inhibitor / report["ki_bound"] if report["ki_bound"] is not None else 1
    return (
        report["vmax"]
        * substrate ** report["hill"]
        / (report["km"] ** report["hill"] * free + substrate ** report["hill"] * bound)
    )


class ScienceKinetics(Scenario):
    family = "science"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        mechanisms = MECHANISMS if level == 3 else MECHANISMS[:3]
        mechanism = self.rng.choice(mechanisms)
        vmax_values = [4, 6, 9] if split == "train" else [5, 7, 10]
        km_values = [2, 5, 10] if split == "train" else [3, 7, 12]
        free_values = [1, 3, 6] if split == "train" else [2, 4, 8]
        bound_values = [2, 4, 8] if split == "train" else [1, 5, 9]
        ki = self.rng.choice(free_values)
        self.parameters = {
            "mechanism": mechanism,
            "hill": self.rng.choice([1, 2]) if level == 3 else 1,
            "vmax": self.rng.choice(vmax_values),
            "km": self.rng.choice(km_values),
            "ki_free": ki if mechanism != "uncompetitive" else None,
            "ki_bound": ki
            if mechanism == "noncompetitive"
            else self.rng.choice(bound_values)
            if mechanism == "mixed"
            else ki
            if mechanism == "uncompetitive"
            else None,
            "signal_gain": self.rng.choice([0.7, 1.2, 1.8]),
            "signal_offset": self.rng.choice([0.2, 0.5, 1.0]),
        }
        unit = "mM" if level == 2 and split == "train" else "uM"
        self.resources = {
            "protocol": {
                "goal": "Identify the inhibition mechanism and a quantitative kinetic hypothesis by designing reproducible, calibrated experiments. Signal=gain*activity+offset. activity=vmax*S^hill / (km^hill*(1+I/ki_free)+S^hill*(1+I/ki_bound)); a null ki means its factor is 1. Competitive: ki_bound=null; uncompetitive: ki_free=null; noncompetitive: both equal; mixed: both positive and unequal. Blank has true activity 0; standard has true activity 2. Use controls to estimate gain and offset, baseline substrate contrasts with I=0, inhibited contrasts at the same substrate concentrations, and repeat one positive assay in a later run to demonstrate reproduction. Fit the measured evidence before verify and commit. Small measurement noise is expected; at least two replicates per required run. Hypothesis predictions are checked at additional conditions following the same published equation. Assays only report real signal readings; they do not disclose the mechanism or kinetic parameters.",
                "mechanisms": mechanisms,
                "delivery_concentration_unit": unit,
                "unit_to_mM": {"mM": 1, "uM": 0.001},
                "candidate_vmax": vmax_values,
                "candidate_hill": [1, 2] if level == 3 else [1],
                "candidate_km": km_values,
                "candidate_ki_free": free_values,
                "candidate_ki_bound": sorted(set(free_values + bound_values)),
                "signal_noise": "Each replicate has independent bounded relative noise of at most 0.2% (using a deterministic seeded simulator).",
                "maximum_assay_runs": 12,
            },
            "notebook": [],
            "hypothesis": {},
        }
        self.instruction = "Form a mechanistic scientific hypothesis through controlled experiments. Calibrate the assay instrument with blank and known-activity standard, choose informative substrate/inhibitor conditions, repeat an assay, fit a hypothesis, inspect measured-versus-predicted evidence and verify before committing."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "hypothesis": "params={mechanism,hill,vmax,km,ki_free,ki_bound,signal_gain,signal_offset}; null ki removes that inhibition factor"
            },
            "run": {
                "calculate": "params={expression:string,variables:{name:number or {num,den}}}; exact arithmetic with abs, ceil, floor, round_half_up; computes supplied numbers only",
                "fit": "params={mechanism:one declared mechanism,hill:one declared exponent}; reproducibly fit ONLY this chosen model to measured notebook evidence using public candidate constants and measured controls. Returns a proposed hypothesis and squared signal residual; does not choose a model, design experiments, or modify the hypothesis.",
                "blank": "params={replicates:2..5}; measure a zero-activity blank",
                "standard": "params={replicates:2..5}; measure a true-activity-2 calibrant",
                "assay": "params={substrate:number,inhibitor:number,unit:mM|uM,replicates:2..5}; execute a kinetic assay",
                "analyze": "params={}; show actual measured-versus-hypothesis signal residuals",
                "verify": "params={}; execute experiment-quality and measured-fit checks; frozen artifact is graded on mechanistic and new-condition predictions",
            },
        }

    def patch(self, target, params):
        if (
            target != "hypothesis"
            or set(params) != FIELDS
            or params["mechanism"] not in self.resources["protocol"]["mechanisms"]
        ):
            raise ValueError(
                "Provide every hypothesis field and an available mechanism"
            )
        for key, value in params.items():
            if key == "mechanism" or key in ["ki_free", "ki_bound"] and value is None:
                continue
            if (
                type(value) not in [int, float]
                or not math.isfinite(value)
                or abs(value) > 100
            ):
                raise ValueError("Use finite bounded numeric hypothesis parameters")
        if any(params[key] <= 0 for key in ["vmax", "km", "signal_gain"]) or any(
            params[key] is not None and params[key] <= 0
            for key in ["ki_free", "ki_bound"]
        ):
            raise ValueError("Kinetic constants and gain must be positive")
        if (
            type(params["hill"]) is not int
            or params["hill"] not in self.resources["protocol"]["candidate_hill"]
        ):
            raise ValueError("Select a declared integer Hill exponent")
        name = params["mechanism"]
        free, bound = params["ki_free"], params["ki_bound"]
        if not (
            name == "competitive"
            and free is not None
            and bound is None
            or name == "uncompetitive"
            and free is None
            and bound is not None
            or name == "noncompetitive"
            and free is not None
            and bound == free
            or name == "mixed"
            and free is not None
            and bound is not None
            and free != bound
        ):
            raise ValueError("ki parameters must match the declared mechanism")
        self.resources["hypothesis"] = dict(params)
        self.version += 1
        return {"hypothesis_updated": True, "version": self.version}

    def run(self, target, params):
        if target == "calculate":
            return calculate(params)
        if target == "fit":
            protocol = self.resources["protocol"]
            rows = self.resources["notebook"]
            if (
                set(params) != {"mechanism", "hill"}
                or params["mechanism"] not in protocol["mechanisms"]
                or type(params["hill"]) is not int
                or params["hill"] not in protocol["candidate_hill"]
            ):
                raise ValueError("Choose a declared mechanism and Hill exponent to fit")
            blanks = [r["signal_mean"] for r in rows if r["kind"] == "blank"]
            standards = [r["signal_mean"] for r in rows if r["kind"] == "standard"]
            assays = [r for r in rows if r["kind"] == "assay" and r["substrate_mM"] > 0]
            if not blanks or not standards or not assays:
                raise ValueError(
                    "Measure blank, standard and at least one positive assay before fitting"
                )
            offset = sum(blanks) / len(blanks)
            gain = (sum(standards) / len(standards) - offset) / 2
            if gain <= 0:
                raise ValueError("Calibrated gain must be positive")
            name = params["mechanism"]
            choices = (
                [(x, None) for x in protocol["candidate_ki_free"]]
                if name == "competitive"
                else [(None, x) for x in protocol["candidate_ki_bound"]]
                if name == "uncompetitive"
                else [(x, x) for x in protocol["candidate_ki_free"]]
                if name == "noncompetitive"
                else [
                    (x, y)
                    for x, y in product(
                        protocol["candidate_ki_free"], protocol["candidate_ki_bound"]
                    )
                    if x != y
                ]
            )
            fits = []
            for vmax, km, (free, bound) in product(
                protocol["candidate_vmax"], protocol["candidate_km"], choices
            ):
                hypothesis = {
                    "mechanism": name,
                    "hill": params["hill"],
                    "vmax": vmax,
                    "km": km,
                    "ki_free": free,
                    "ki_bound": bound,
                    "signal_gain": gain,
                    "signal_offset": offset,
                }
                residual = sum(
                    (
                        gain
                        * activity(hypothesis, r["substrate_mM"], r["inhibitor_mM"])
                        + offset
                        - r["signal_mean"]
                    )
                    ** 2
                    for r in assays
                )
                fits.append((residual, hypothesis))
            error, proposed = min(fits, key=lambda item: item[0])
            return {
                "chosen_model": dict(params),
                "proposed_hypothesis": proposed,
                "squared_signal_residual": error,
                "assays_used": len(assays),
                "note": "Observed-data fit only; choose the mechanism and exponent using informative measured contrasts, then patch hypothesis and verify.",
            }
        if target in ["blank", "standard", "assay"]:
            if len(self.resources["notebook"]) >= 12:
                raise ValueError("Assay run budget exhausted")
            expected = (
                {"replicates", "substrate", "inhibitor", "unit"}
                if target == "assay"
                else {"replicates"}
            )
            if (
                set(params) != expected
                or type(params["replicates"]) is not int
                or not 2 <= params["replicates"] <= 5
            ):
                raise ValueError("Use the declared assay parameters and 2–5 replicates")
            substrate = inhibitor = 0.0
            if target == "assay":
                if params["unit"] not in self.resources["protocol"][
                    "unit_to_mM"
                ] or any(
                    type(params[k]) not in [int, float]
                    or not math.isfinite(params[k])
                    or not 0 <= params[k] <= 100000
                    for k in ["substrate", "inhibitor"]
                ):
                    raise ValueError(
                        "Use finite nonnegative concentrations and a declared unit"
                    )
                scale = self.resources["protocol"]["unit_to_mM"][params["unit"]]
                substrate = float(
                    Fraction(str(params["substrate"])) * Fraction(str(scale))
                )
                inhibitor = float(
                    Fraction(str(params["inhibitor"])) * Fraction(str(scale))
                )
            rate = (
                0
                if target == "blank"
                else 2
                if target == "standard"
                else activity(self.parameters, substrate, inhibitor)
            )
            signal = (
                self.parameters["signal_gain"] * rate + self.parameters["signal_offset"]
            )
            readings = [
                signal + self.rng.uniform(-0.002, 0.002) * max(1, abs(signal))
                for _ in range(params["replicates"])
            ]
            row = {
                "kind": target,
                "substrate_mM": substrate,
                "inhibitor_mM": inhibitor,
                "readings": readings,
                "signal_mean": sum(readings) / len(readings),
                "replicates": len(readings),
                "run_index": len(self.resources["notebook"]),
            }
            self.resources["notebook"].append(row)
            self.version += 1
            progress = self.checks()
            return {
                **copy.deepcopy(row),
                "remaining_assay_runs": 12 - len(self.resources["notebook"]),
                "experiment_progress": {
                    k: progress[k]
                    for k in [
                        "calibration_controls_measured",
                        "baseline_and_inhibited_contrasts",
                        "positive_assay_reproduced",
                    ]
                },
            }
        if target not in ["analyze", "verify"] or params:
            raise ValueError("Run a declared assay, analyze or verify")
        report = self.resources["hypothesis"]
        if not report:
            raise ValueError("Enter a quantitative hypothesis first")
        residuals = []
        for row in self.resources["notebook"]:
            rate = (
                0
                if row["kind"] == "blank"
                else 2
                if row["kind"] == "standard"
                else activity(report, row["substrate_mM"], row["inhibitor_mM"])
            )
            predicted = report["signal_gain"] * rate + report["signal_offset"]
            residuals.append(
                {
                    "run_index": row["run_index"],
                    "predicted_signal": predicted,
                    "observed_signal": row["signal_mean"],
                    "residual": predicted - row["signal_mean"],
                }
            )
        diagnostic = self.checks()
        public = {
            k: v
            for k, v in diagnostic.items()
            if k not in ["mechanism_identified", "new_condition_predictions_match"]
        }
        if target == "verify":
            self.artifact = {
                "report": dict(report),
                "notebook": copy.deepcopy(self.resources["notebook"]),
            }
            self.receipt_version = self.version
        return {
            "measured_fit": residuals,
            "experiment_diagnostics": public,
            "version": self.version,
        }

    def checks(self):
        rows = self.resources["notebook"]
        report = self.resources["hypothesis"]
        assays = [r for r in rows if r["kind"] == "assay"]
        baselines = {
            r["substrate_mM"]
            for r in assays
            if r["inhibitor_mM"] == 0 and r["substrate_mM"] > 0
        }
        inhibited = {
            r["substrate_mM"]
            for r in assays
            if r["inhibitor_mM"] > 0 and r["substrate_mM"] > 0
        }
        conditions = [
            (r["substrate_mM"], r["inhibitor_mM"])
            for r in assays
            if r["substrate_mM"] > 0 and r["inhibitor_mM"] > 0
        ]
        controls = all(
            any(r["kind"] == kind and r["replicates"] >= 2 for r in rows)
            for kind in ["blank", "standard"]
        )
        fit = bool(report and rows)
        if fit:
            for row in rows:
                rate = (
                    0
                    if row["kind"] == "blank"
                    else 2
                    if row["kind"] == "standard"
                    else activity(report, row["substrate_mM"], row["inhibitor_mM"])
                )
                predicted = report["signal_gain"] * rate + report["signal_offset"]
                fit &= abs(predicted - row["signal_mean"]) <= max(
                    0.02, 0.03 * abs(row["signal_mean"])
                )
        predictions = bool(report)
        if predictions:
            for substrate, inhibitor in [(0.7, 0.5), (3, 2), (12, 7), (30, 11)]:
                true = activity(self.parameters, substrate, inhibitor)
                estimate = activity(report, substrate, inhibitor)
                predictions &= abs(true - estimate) <= 0.04 * max(0.1, true)
        return {
            "calibration_controls_measured": bool(controls),
            "baseline_and_inhibited_contrasts": bool(
                len(baselines) >= 2 and len(baselines & inhibited) >= 2
            ),
            "positive_assay_reproduced": bool(len(set(conditions)) < len(conditions)),
            "hypothesis_fits_measured_evidence": bool(fit),
            "mechanism_identified": bool(
                report and report["mechanism"] == self.parameters["mechanism"]
            ),
            "new_condition_predictions_match": bool(predictions),
        }
