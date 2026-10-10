"""Visible frozen task metadata, never answers or grading fixtures."""

import hashlib
import json
from pathlib import Path
from .task_ids import FAMILIES

TASK_BANK = [
    {
        "task_id": f"{family}-case{index + 1}",
        "family": family,
        "level": index % 3 + 1,
        "seed": 2600000 + family_index * 1000 + (index % 3 + 1) * 100 + index // 3,
        "split": "train",
    }
    for family_index, family in enumerate(FAMILIES)
    for index in range(6)
]


def release_revision():
    from workflow_controller.engine import revision

    source = Path(__file__).parent
    h = hashlib.sha256(revision().encode())
    for path in sorted(source.glob("*.py")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    bank = source / "frozen_tasks.json"
    if bank.exists():
        h.update(bank.read_bytes())
    return h.hexdigest()


def tasks():
    path = Path(__file__).with_name("frozen_tasks.json")
    rows = json.loads(path.read_text()) if path.exists() else TASK_BANK
    expected = {"task_id", "family", "level", "seed", "split"}
    if not isinstance(rows, list) or len(rows) != 48:
        raise ValueError("Invalid frozen task bank size")
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != expected
            or row["family"] not in FAMILIES
            or type(row["level"]) is not int
            or row["level"] not in [1, 2, 3]
            or type(row["seed"]) is not int
            or row["seed"] < 0
            or row["split"] != "train"
        ):
            raise ValueError("Invalid frozen task metadata")
    ids = {r["task_id"] for r in rows}
    for family in FAMILIES:
        members = [r for r in rows if r["family"] == family]
        if (
            len(members) != 6
            or {r["level"] for r in members} != {1, 2, 3}
            or {r["task_id"] for r in members}
            != {f"{family}-case{i}" for i in range(1, 7)}
        ):
            raise ValueError("Invalid frozen domain coverage")
    if len(ids) != 48:
        raise ValueError("Duplicate frozen task identifier")
    return rows
