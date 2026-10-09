"""Read this account's submission and run status without exposing credentials."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from huggingface_hub import get_token
from scripts.hf_account import board_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", default="reconcile-lab-v1")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    token = get_token()
    if not token:
        raise SystemExit("Authenticate with Hugging Face locally before reading your submission.")
    submission = board_request("/submissions/" + args.submission, token=token)
    run_reference = submission.get("run") or {}
    run_id = run_reference.get("run_id")
    run = board_request("/runs/" + run_id, token=token) if run_id else None
    if args.save:
        reports = Path("reports")
        reports.mkdir(exist_ok=True)
        (reports / "arena-submission-status.json").write_text(json.dumps(submission, indent=2) + "\n")
        if run:
            (reports / "arena-run-status.json").write_text(json.dumps(run, indent=2) + "\n")
    output = {"submission_id": args.submission, "state": submission.get("state"), "simulated": submission.get("simulated"), "slot": submission.get("slot"), "admission": submission.get("admission"), "errors": submission.get("report", {}).get("errors"), "error_code": submission.get("error_code"), "error_origin": submission.get("error_origin"), "run_reference": run_reference, "run": run}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
