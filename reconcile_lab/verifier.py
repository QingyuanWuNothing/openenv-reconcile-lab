"""Independent Python verifier. SQL is a tool, never the grading mechanism."""

import math
from .tasks import Case, audit_parameters


def newest(rows: list[dict], keys: tuple[str, ...], revision: str) -> list[dict]:
    selected = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key not in selected or row[revision] > selected[key][revision]:
            selected[key] = row
    return list(selected.values())


def expected_report(case: Case) -> dict[str, float]:
    t = case.tables
    if "invoices" in t:
        cutoff = audit_parameters(case)["cutoff_day"]
        rates = {r["currency"]: r["usd_rate"] for r in t["fx"]}
        regions = {r["customer_id"]: r["region"] for r in t["customers"]}
        delta = {}
        for r in newest(t["events"], ("event_id",), "version"):
            if r["status"] == "posted" and r["day"] <= cutoff:
                delta[r["invoice_id"]] = delta.get(r["invoice_id"], 0) + r["amount"] * (-1 if r["kind"] == "payment" else 1)
        total, north, unpaid = 0.0, 0.0, 0
        for r in t["invoices"]:
            if r["status"] != "approved" or r["issued_day"] > cutoff:
                continue
            balance = max(0, r["amount"] + delta.get(r["invoice_id"], 0))
            usd = balance * rates[r["currency"]]
            total += usd
            north += usd if regions[r["customer_id"]] == "north" else 0
            unpaid += balance > 0
        return {"outstanding_usd": round(total, 2), "north_outstanding_usd": round(north, 2), "unpaid_invoices": unpaid}
    if "samples" in t:
        batches = {r["batch_id"]: r for r in t["batches"]}
        values = {}
        for r in newest(t["readings"], ("sample_id", "replicate_id"), "revision"):
            if r["valid"] == 1:
                values.setdefault(r["sample_id"], []).append(r["raw"])
        arms = {"control": [], "treatment": []}
        for s in t["samples"]:
            b = batches[s["batch_id"]]
            if s["excluded"] or b["qc"] != "pass" or s["sample_id"] not in values:
                continue
            readings = values[s["sample_id"]]
            mean = sum((v - b["offset"]) / b["gain"] for v in readings) / len(readings)
            arms[s["arm"]].append(mean)
        return {"treatment_mean": round(sum(arms["treatment"]) / len(arms["treatment"]), 2), "control_mean": round(sum(arms["control"]) / len(arms["control"]), 2), "eligible_samples": sum(map(len, arms.values()))}
    now = audit_parameters(case)["audit_minute"]
    allowances = {r["team_id"]: r["sla_minutes"] for r in t["teams"]}
    events = newest(t["events"], ("ticket_id", "event_seq"), "revision")
    opened, breaches, total = 0, 0, 0
    for ticket in t["tickets"]:
        state, last, active = "active", ticket["opened_minute"], 0
        timeline = sorted((e for e in events if e["ticket_id"] == ticket["ticket_id"] and e["minute"] <= now), key=lambda r: r["minute"])
        for e in timeline:
            if state == "active":
                active += e["minute"] - last
            last, state = e["minute"], e["state"]
        if state == "active":
            active += now - last
        is_open = state != "closed"
        allowance = allowances[ticket["team_id"]] / (2 if ticket["priority"] == "urgent" else 1)
        opened += is_open
        breaches += is_open and active > allowance
        total += active
    return {"open_tickets": opened, "breached_tickets": breaches, "total_active_minutes": total}


def grade(case: Case, report: dict) -> tuple[float, dict[str, bool]]:
    expected = expected_report(case)
    checks = {}
    for key, answer in expected.items():
        value = report.get(key)
        # Bool is an int subclass, but is not a legitimate numeric report value.
        try:
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        except (OverflowError, ValueError):
            valid = False
        tolerance = 0.011 if key.endswith("mean") or key.endswith("usd") else 1e-9
        checks[key] = bool(valid and abs(value - answer) <= tolerance)
    return sum(checks.values()) / len(checks), checks
