"""Mutable journal close with revisions, settlement and exact currency arithmetic."""

import copy
from fractions import Fraction

from .scenarios import Scenario


class Finance(Scenario):
    family = "finance"

    def __init__(self, seed, level, split="train"):
        super().__init__(seed, level, split)
        cutoff = self.rng.randint(12, 20)
        rows = []
        for i in range(3 + 2 * level):
            r = {
                "id": f"t{i}",
                "revision": 1,
                "day": self.rng.randint(1, 24),
                "amount_minor": self.rng.randint(10, 120) * 10,
                "currency": self.rng.choice(
                    ["GBP", "USD"] if split == "train" else ["GBP", "USD", "EUR"]
                ),
                "direction": self.rng.choice(["in", "out"]),
                "status": "settled"
                if level == 1
                else self.rng.choice(["settled", "settled", "pending"]),
            }
            rows.append(r)
            if level == 3 and i % 2 == 0:
                rows.append(
                    dict(
                        r,
                        revision=2,
                        amount_minor=r["amount_minor"] + self.rng.randint(1, 9),
                        status=self.rng.choice(["settled", "pending"]),
                    )
                )
        rows[0].update(status="settled", day=1)
        self.rng.shuffle(rows)
        self.resources = {
            "policy": {
                "cutoff_day": cutoff,
                "opening_cash_minor": 25000,
                "fx_to_gbp": {"GBP": [1, 1], "USD": [4, 5], "EUR": [7, 8]},
                "rule": "Keep the latest revision per transaction ID BEFORE filtering. Post exactly one journal entry for each retained settled transaction on/before cutoff. Exclude pending/future records. Convert each amount to GBP minor units using the exact numerator/denominator rate, rounding positive magnitudes half-up to the nearest integer, then apply sign (in=positive,out=negative). Never round the aggregate instead of individual transactions. Close the ledger and reconcile inflow, outflow and ending cash.",
            },
            "transactions": rows,
            "journal": [],
        }
        self.instruction = "Investigate and reconcile this cash ledger. Inspect policy and source transactions, post signed entries, run the closing process and inspect reconciliation diagnostics. Revise discrepancies before committing the actual closed journal. Source records, rates and cutoff are immutable."
        self.tools = {
            "inspect": list(self.resources),
            "patch": {
                "entry": "params={transaction_id:string,gbp_minor:integer}; upserts one entry",
                "journal": "params={entries:[{transaction_id,gbp_minor},...]}; replaces all entries",
            },
            "run": {
                "close": "params={} executes posting and returns cash/inflow/outflow totals with reconciliation diagnostics"
            },
        }

    def wanted(self):
        latest = {}
        for r in self.resources["transactions"]:
            if r["id"] not in latest or r["revision"] > latest[r["id"]]["revision"]:
                latest[r["id"]] = r
        result = {}
        p = self.resources["policy"]
        for key, r in latest.items():
            if r["status"] == "settled" and r["day"] <= p["cutoff_day"]:
                num, den = p["fx_to_gbp"][r["currency"]]
                amount = Fraction(r["amount_minor"] * num, den)
                rounded = (2 * amount.numerator + amount.denominator) // (
                    2 * amount.denominator
                )
                result[key] = rounded * (1 if r["direction"] == "in" else -1)
        return result

    def patch(self, target, params):
        if target == "entry":
            if set(params) != {"transaction_id", "gbp_minor"}:
                raise ValueError("Provide a complete journal entry")
            rows = [
                r
                for r in self.resources["journal"]
                if r["transaction_id"] != params["transaction_id"]
            ] + [params]
        elif target == "journal" and set(params) == {"entries"}:
            rows = params["entries"]
        else:
            raise ValueError("Patch entry or journal")
        if (
            not isinstance(rows, list)
            or len(rows) > 30
            or any(
                not isinstance(r, dict)
                or set(r) != {"transaction_id", "gbp_minor"}
                or not isinstance(r["transaction_id"], str)
                or type(r["gbp_minor"]) is not int
                or abs(r["gbp_minor"]) > 1000000
                for r in rows
            )
        ):
            raise ValueError("Malformed journal entries")
        self.resources["journal"] = copy.deepcopy(rows)
        self.version += 1
        return {"entries": len(rows), "version": self.version}

    def run(self, target, params):
        if target != "close" or params:
            raise ValueError("Run close with params={}")
        rows = self.resources["journal"]
        self.artifact = {
            "posted": copy.deepcopy(rows),
            "ending_cash_minor": 25000 + sum(r["gbp_minor"] for r in rows),
            "inflow_minor": sum(max(0, r["gbp_minor"]) for r in rows),
            "outflow_minor": sum(max(0, -r["gbp_minor"]) for r in rows),
        }
        self.receipt_version = self.version
        return {
            **{k: v for k, v in self.artifact.items() if k != "posted"},
            "diagnostics": self.checks(),
            "version": self.version,
        }

    def checks(self):
        a = self.artifact or {}
        rows = a.get("posted", [])
        actual = {r["transaction_id"]: r["gbp_minor"] for r in rows}
        wanted = self.wanted()
        return {
            "coverage_exact": len(rows) == len(wanted) and set(actual) == set(wanted),
            "individual_postings_reconcile": actual == wanted,
            "close_reconciles": a.get("ending_cash_minor")
            == 25000 + sum(wanted.values())
            and a.get("inflow_minor") == sum(max(0, x) for x in wanted.values())
            and a.get("outflow_minor") == sum(max(0, -x) for x in wanted.values()),
        }
