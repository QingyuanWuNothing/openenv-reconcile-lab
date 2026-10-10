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
    if len(rows) > 50 or len({r["task_id"] for r in rows}) != len(rows):
        raise ValueError("Invalid frozen task bank")
    return rows
