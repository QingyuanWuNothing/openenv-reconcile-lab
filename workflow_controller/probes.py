"""Unseen-domain evaluation tasks; excluded from the training curriculum."""

import copy
import math

from .scenarios import Scenario


class ScienceProbe(Scenario):
    family = "science"

    def __init__(self, seed, level, split="holdout"):
        super().__init__(seed, level, split)
        slope = self.rng.choice([1.3, 1.7, 2.1, 2.6])
        offset = self.rng.choice([-0.4, 0.2, 0.6])
        rows = []
        for i in range(6 + level):
            x = i / 2
            rows.append(
                {
                    "id": f"m{i}",
                    "time_s": x,
                    "distance": round(offset + slope * x, 6),
                    "quality": "valid",
                }
            )
        if level >= 2:
            rows[1].update(
                distance=round(rows[1]["distance"] + 3.0, 6), quality="sensor_fault"
            )
        unit = "cm" if level == 3 else "m"
        if unit == "cm":
            for row in rows:
                row["distance"] = round(row["distance"] * 100, 6)
        self.resources = {
            "protocol": {
                "goal": "Estimate velocity in m/s using every valid row and no sensor_fault rows. Fit an intercept; convert source distances to meters before fitting. Run the experiment and inspect its reproducible fit.",
                "distance_unit": unit,
                "time_unit": "s",
                "model": "distance_m = intercept_m + velocity_m_s * time_s",
            },
            "measurements": rows,
            "analysis": {
                "included_ids": [],
                "distance_scale": 1,
                "fit_intercept": False,
            },
        }
        self.instruction = "Analyze this independent motion experiment. Read the protocol and measurements, choose a reproducible analysis, run the fit, inspect evidence and commit the result. The underlying physics and records are fixed."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "analysis": "params={included_ids:[id,...],distance_scale:number,fit_intercept:boolean}"
            },
            "run": {
                "experiment": "params={} performs an actual least-squares fit and returns coefficients, residuals and included IDs"
            },
        }

    def patch(self, target, params):
        if target != "analysis" or set(params) != {
            "included_ids",
            "distance_scale",
            "fit_intercept",
        }:
            raise ValueError("Replace the complete analysis configuration")
        if (
            not isinstance(params["included_ids"], list)
            or any(not isinstance(x, str) for x in params["included_ids"])
            or len(params["included_ids"]) > 20
        ):
            raise ValueError("Invalid measurement IDs")
        if (
            type(params["distance_scale"]) not in [int, float]
            or not 0.001 <= params["distance_scale"] <= 10
            or type(params["fit_intercept"]) is not bool
        ):
            raise ValueError("Invalid fit configuration")
        self.resources["analysis"] = copy.deepcopy(params)
        self.version += 1
        return {"configuration_version": self.version}

    def fit(self, rows, scale, intercept):
        if len(rows) < 2:
            raise ValueError("At least two measurements required")
        xs, ys = [r["time_s"] for r in rows], [r["distance"] * scale for r in rows]
        xm, ym = (sum(xs) / len(xs), sum(ys) / len(ys)) if intercept else (0, 0)
        denominator = sum((x - xm) ** 2 for x in xs)
        if not denominator:
            raise ValueError("Measurements need distinct times")
        slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denominator
        offset = ym - slope * xm
        return {
            "velocity_m_s": slope,
            "intercept_m": offset,
            "residual_sum_squares": sum(
                (y - offset - slope * x) ** 2 for x, y in zip(xs, ys)
            ),
        }

    def run(self, target, params):
        if target != "experiment" or params:
            raise ValueError("Run experiment with params={}")
        config = self.resources["analysis"]
        by_id = {r["id"]: r for r in self.resources["measurements"]}
        if any(k not in by_id for k in config["included_ids"]):
            raise ValueError("Unknown measurement")
        rows = [by_id[k] for k in config["included_ids"]]
        self.artifact = dict(
            self.fit(rows, config["distance_scale"], config["fit_intercept"]),
            included_ids=list(config["included_ids"]),
        )
        self.receipt_version = self.version
        return copy.deepcopy(self.artifact)

    def checks(self):
        valid = [r for r in self.resources["measurements"] if r["quality"] == "valid"]
        scale = 0.01 if self.resources["protocol"]["distance_unit"] == "cm" else 1
        # Independent closed-form recomputation from immutable observed records.
        n = len(valid)
        sx = sum(r["time_s"] for r in valid)
        sy = sum(r["distance"] * scale for r in valid)
        sxx = sum(r["time_s"] ** 2 for r in valid)
        sxy = sum(r["time_s"] * r["distance"] * scale for r in valid)
        velocity = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        offset = (sy - velocity * sx) / n
        a = self.artifact or {}
        ids = a.get("included_ids", [])
        return {
            "protocol_followed": len(ids) == len(valid)
            and set(ids) == {r["id"] for r in valid}
            and self.resources["analysis"]["fit_intercept"]
            and self.resources["analysis"]["distance_scale"] == scale,
            "velocity_matches_evidence": math.isclose(
                a.get("velocity_m_s", math.inf), velocity, abs_tol=1e-6
            ),
            "intercept_matches_evidence": math.isclose(
                a.get("intercept_m", math.inf), offset, abs_tol=1e-6
            ),
        }


class FinanceProbe(Scenario):
    family = "finance"

    def __init__(self, seed, level, split="holdout"):
        super().__init__(seed, level, split)
        rows = [
            {
                "id": f"t{i}",
                "amount_minor": self.rng.randrange(5, 80) * 100,
                "currency": "USD" if level == 3 and i % 2 else "GBP",
                "status": "pending" if level >= 2 and i == 1 else "settled",
                "direction": "in" if i % 3 else "out",
                "reverses": None,
            }
            for i in range(4 + level)
        ]
        if level >= 2:
            first = rows[0]
            rows.append(dict(first, id="refund", direction="in", reverses=first["id"]))
        self.resources = {
            "policy": {
                "goal": "Post exactly one signed GBP minor-unit entry for each settled transaction; exclude pending. A settled reversal is a separate opposite-direction entry, so the original and reversal both appear and cancel. Convert each USD transaction at the given exact rational rate; all provided amounts convert exactly.",
                "fx_to_gbp": {"GBP": [1, 1], "USD": [4, 5]},
                "opening_cash_minor": 25000,
            },
            "transactions": rows,
            "journal": [],
        }
        self.instruction = "Reconcile and close this cash ledger. Inspect records and policy, prepare journal entries, run the closing process and inspect its balances. Correct discrepancies and commit a reproducible close."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "journal": "params={entries:[{transaction_id:string,gbp_minor:integer},...]}; positive=inflow, negative=outflow"
            },
            "run": {
                "close": "params={} posts entries and computes closing cash, inflow and outflow totals"
            },
        }

    def patch(self, target, params):
        rows = params.get("entries")
        if (
            target != "journal"
            or set(params) != {"entries"}
            or not isinstance(rows, list)
            or len(rows) > 30
        ):
            raise ValueError("Replace journal entries")
        if any(
            not isinstance(r, dict)
            or set(r) != {"transaction_id", "gbp_minor"}
            or not isinstance(r["transaction_id"], str)
            or type(r["gbp_minor"]) is not int
            or abs(r["gbp_minor"]) > 1000000
            for r in rows
        ):
            raise ValueError("Malformed journal entry")
        self.resources["journal"] = copy.deepcopy(rows)
        self.version += 1
        return {"journal_entries": len(rows), "configuration_version": self.version}

    def run(self, target, params):
        if target != "close" or params:
            raise ValueError("Run close with params={}")
        rows = self.resources["journal"]
        self.artifact = {
            "posted_entries": copy.deepcopy(rows),
            "closing_cash_minor": 25000 + sum(r["gbp_minor"] for r in rows),
            "inflow_minor": sum(max(0, r["gbp_minor"]) for r in rows),
            "outflow_minor": sum(max(0, -r["gbp_minor"]) for r in rows),
        }
        self.receipt_version = self.version
        return copy.deepcopy(self.artifact)

    def checks(self):
        wanted = {}
        for r in self.resources["transactions"]:
            if r["status"] != "settled":
                continue
            num, den = self.resources["policy"]["fx_to_gbp"][r["currency"]]
            wanted[r["id"]] = (
                r["amount_minor"] * num // den * (1 if r["direction"] == "in" else -1)
            )
        a = self.artifact or {}
        rows = a.get("posted_entries", [])
        actual = {r["transaction_id"]: r["gbp_minor"] for r in rows}
        return {
            "transaction_coverage": len(rows) == len(wanted)
            and set(actual) == set(wanted),
            "journal_amounts_reconcile": actual == wanted,
            "closing_cash_reconciles": a.get("closing_cash_minor")
            == 25000 + sum(wanted.values()),
        }


PROBES = {cls.family + "-probe": cls for cls in [ScienceProbe, FinanceProbe]}
