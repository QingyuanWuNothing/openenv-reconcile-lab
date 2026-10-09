"""Write a reviewable request; this command never submits it."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconcile_lab.tasks import TASKS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--image", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", default="submission.json")
    args = parser.parse_args()
    with urllib.request.urlopen(args.url.rstrip("/") + "/schema", timeout=10) as response:
        schema = json.load(response)
    request = {
        "submission_id": "reconcile-lab-v1",
        "name": "Reconcile Lab",
        "image": args.image,
        "schema": {k: schema[k] for k in ["action", "observation"]},
        "tasks": [dict(task_id=t["task_id"], split="train", reset_wall_s=120, rollout_wall_s=900, verifier_wall_s=30, tool_wall_s=30, tool_calls_total=24, completion_tokens=8192, context_tokens=16384, memory_gib=2, cpu_floor_vcpus=1, workspace_gib=1) for t in TASKS],
        "example_actions": [{"op": "finish"}],
        "finish_action": {"op": "finish"},
        "dataset": args.dataset,
        "source": args.source,
    }
    Path(args.output).write_text(json.dumps(request, indent=2) + "\n")
    print(f"Prepared {args.output}; no request sent.")


if __name__ == "__main__":
    main()
