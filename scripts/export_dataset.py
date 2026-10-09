"""Create the public dataset payload, containing inputs but no reference reports."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconcile_lab.tasks import TASKS, audit_parameters, generate


def main():
    destination = Path("dataset")
    destination.mkdir(exist_ok=True)
    with (destination / "tasks.jsonl").open("w") as handle:
        for t in TASKS:
            handle.write(json.dumps(t) + "\n")
    with (destination / "examples.jsonl").open("w") as handle:
        for task in TASKS:
            for seed in [0, 17, 53]:
                case = generate(task["task_id"], seed)
                record = {"task_id": task["task_id"], "seed": seed, "instruction": case.instruction, "columns": case.columns, "tables": case.tables, "metrics": case.metrics, "parameters": audit_parameters(case)}
                handle.write(json.dumps(record) + "\n")
    print("Exported nine task settings and 27 seeded input examples; no reference reports.")


if __name__ == "__main__":
    main()
