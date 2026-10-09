"""Generate original task data. No reference answer is stored with the data."""

from dataclasses import dataclass
import random


TASKS = [
    {"task_id": f"{family}-l{level}", "family": family, "level": level, "split": "train"}
    for family in ("finance", "science", "office")
    for level in (1, 2, 3)
]


@dataclass
class Case:
    instruction: str
    tables: dict[str, list[dict]]
    columns: dict[str, dict[str, str]]
    metrics: list[str]


def generate(task_id: str, seed: int) -> Case:
    spec = next((t for t in TASKS if t["task_id"] == task_id), None)
    if spec is None:
        raise ValueError(f"Unknown task_id: {task_id}")
    rng = random.Random(seed)
    return {"finance": finance, "science": science, "office": office}[spec["family"]](rng, spec["level"])


def finance(rng: random.Random, level: int) -> Case:
    cutoff = rng.randint(18, 26)
    customers = [{"customer_id": i, "region": rng.choice(["north", "south"])} for i in range(1, 9)]
    invoices, events = [], []
    sequence = 0
    for i in range(1, 7 + 6 * level):
        inv = {"invoice_id": i, "customer_id": rng.randint(1, 8), "currency": rng.choice(["USD", "EUR", "GBP"]), "amount": rng.randint(30, 500), "status": rng.choice(["approved", "approved", "void"]), "issued_day": rng.randint(1, 30)}
        invoices.append(inv)
        amount = inv["amount"]
        for n in range(rng.randint(0, level + 1)):
            sequence += 1
            # Repeated export records have the same event_id; latest version wins.
            event = {"event_id": sequence, "invoice_id": i, "kind": rng.choice(["payment", "payment", "refund"]), "amount": rng.randint(1, max(1, amount // 2)), "day": rng.randint(1, 30), "status": "posted", "version": 1}
            if level >= 2:
                event["status"] = rng.choice(["posted", "posted", "pending"])
            events.append(event)
            if level >= 3 and n == 0:
                revised = dict(event, version=2, amount=event["amount"] + rng.randint(1, 15))
                events.append(revised)
    # Include a predictable qualifying record so all quantities are defined.
    invoices[0].update(status="approved", issued_day=1)
    rng.shuffle(invoices)
    rng.shuffle(events)
    fx = [{"currency": c, "usd_rate": r} for c, r in zip(["USD", "EUR", "GBP"], [1.0, rng.choice([1.08, 1.12, 1.16]), rng.choice([1.24, 1.28, 1.32])])]
    return Case(
        f"Prepare the receivables audit at end of day {cutoff}. Include only approved invoices issued on or before that day. For events, keep the highest version per event_id BEFORE applying any status/day filters; retain posted events on or before cutoff. Payments reduce the invoice balance; refunds increase it. Events use their invoice's currency. Outstanding USD is max(0, invoice amount - payments + refunds) * usd_rate, calculated separately per invoice before summing. Report total outstanding_usd, north_outstanding_usd for customers in region north, and unpaid_invoices (count with strictly positive outstanding balance). Round monetary totals to two decimals only after summing. Ignore invoices not included in the audit. Cutoff day={cutoff}.",
        {"customers": customers, "invoices": invoices, "events": events, "fx": fx},
        {"customers": {"customer_id": "INTEGER", "region": "TEXT"}, "invoices": {"invoice_id": "INTEGER", "customer_id": "INTEGER", "currency": "TEXT", "amount": "INTEGER", "status": "TEXT", "issued_day": "INTEGER"}, "events": {"event_id": "INTEGER", "invoice_id": "INTEGER", "kind": "TEXT", "amount": "INTEGER", "day": "INTEGER", "status": "TEXT", "version": "INTEGER"}, "fx": {"currency": "TEXT", "usd_rate": "REAL"}},
        ["outstanding_usd", "north_outstanding_usd", "unpaid_invoices"],
    )


def science(rng: random.Random, level: int) -> Case:
    batches = [{"batch_id": i, "qc": "pass" if i == 1 else rng.choice(["pass", "pass", "fail"]), "offset": rng.randint(1, 8), "gain": rng.choice([1, 2, 4])} for i in range(1, 3 + level)]
    samples, readings = [], []
    for i in range(1, 9 + 5 * level):
        sample = {"sample_id": i, "batch_id": rng.randint(1, len(batches)), "arm": rng.choice(["control", "treatment"]), "excluded": 0 if level == 1 else rng.choice([0, 0, 0, 1])}
        if i <= 2:
            sample.update(batch_id=1, arm="control" if i == 1 else "treatment", excluded=0)
        samples.append(sample)
        for rep in range(1, rng.randint(2, 3 + level)):
            value = {"sample_id": i, "replicate_id": rep, "revision": 1, "raw": rng.randint(15, 120), "valid": 1}
            if level >= 2 and i > 2:
                value["valid"] = rng.choice([1, 1, 0])
            readings.append(value)
            if level == 3 and rep == 1:
                readings.append(dict(value, revision=2, raw=value["raw"] + rng.randint(1, 20), valid=rng.choice([0, 1]) if i > 2 else 1))
    rng.shuffle(readings)
    rng.shuffle(samples)
    return Case(
        "Audit the experiment. First keep the highest revision per (sample_id, replicate_id), THEN retain only valid=1 readings. A sample is eligible when excluded=0, its batch qc='pass', and it has at least one retained reading. Correct each retained reading using (raw - batch.offset) / batch.gain. Average readings within each sample, then give each eligible sample equal weight in its arm mean. Report treatment_mean and control_mean to two decimals, and eligible_samples (the count across both arms). Do not average all readings together: unequal replicate counts must not change sample weights. Round only the final arm means.",
        {"batches": batches, "samples": samples, "readings": readings},
        {"batches": {"batch_id": "INTEGER", "qc": "TEXT", "offset": "INTEGER", "gain": "REAL"}, "samples": {"sample_id": "INTEGER", "batch_id": "INTEGER", "arm": "TEXT", "excluded": "INTEGER"}, "readings": {"sample_id": "INTEGER", "replicate_id": "INTEGER", "revision": "INTEGER", "raw": "REAL", "valid": "INTEGER"}},
        ["treatment_mean", "control_mean", "eligible_samples"],
    )


def office(rng: random.Random, level: int) -> Case:
    now = rng.randint(800, 1200)
    teams = [{"team_id": i, "sla_minutes": rng.choice([120, 180, 240])} for i in range(1, 5)]
    tickets, events = [], []
    for i in range(1, 8 + level * 5):
        opened = rng.randint(1, now - 50)
        ticket = {"ticket_id": i, "team_id": rng.randint(1, 4), "opened_minute": opened, "priority": rng.choice(["normal", "urgent"])}
        tickets.append(ticket)
        times = sorted(rng.sample(range(opened + 1, now + 80), 1 + level))
        for n, at in enumerate(times):
            event = {"ticket_id": i, "event_seq": n + 1, "minute": at, "state": rng.choice(["active", "paused", "closed"]) if level > 1 else rng.choice(["active", "closed"]), "revision": 1}
            events.append(event)
            if level == 3 and n == 0:
                events.append(dict(event, revision=2, state=rng.choice(["active", "paused", "closed"])))
    rng.shuffle(events)
    rng.shuffle(tickets)
    return Case(
        f"Audit ticket SLAs at minute {now}. For each (ticket_id,event_seq), keep the highest revision BEFORE filtering times; ignore events after the audit minute. Every ticket starts active at opened_minute. Apply events in increasing minute order: each changes the state from its timestamp onwards. Only active intervals consume SLA time; paused and closed intervals consume zero. Reopening is possible, so closed is not necessarily final. A ticket is open if its last state is active or paused. Urgent tickets have half their team's sla_minutes allowance; normal tickets have the full allowance. An OPEN ticket is breached when accumulated active_minutes is STRICTLY greater than its allowance. Report open_tickets, breached_tickets (open tickets only), and total_active_minutes (sum across ALL tickets, including closed ones). Audit minute={now}.",
        {"teams": teams, "tickets": tickets, "events": events},
        {"teams": {"team_id": "INTEGER", "sla_minutes": "INTEGER"}, "tickets": {"ticket_id": "INTEGER", "team_id": "INTEGER", "opened_minute": "INTEGER", "priority": "TEXT"}, "events": {"ticket_id": "INTEGER", "event_seq": "INTEGER", "minute": "INTEGER", "state": "TEXT", "revision": "INTEGER"}},
        ["open_tickets", "breached_tickets", "total_active_minutes"],
    )


def audit_parameters(case: Case) -> dict:
    """Public audit parameters, derived from the written brief."""
    if "invoices" in case.tables:
        return {"cutoff_day": int(case.instruction.rsplit("=", 1)[1].rstrip("."))}
    if "tickets" in case.tables:
        return {"audit_minute": int(case.instruction.rsplit("=", 1)[1].rstrip("."))}
    return {}
