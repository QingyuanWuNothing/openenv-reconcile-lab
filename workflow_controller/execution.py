"""Execute restricted agent programs away from controller and checker state."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .safe_worker import validate, METHODS, FUNCTIONS


def execute(source, inputs):
    validate(source)
    payload = json.dumps({"source": source, "inputs": inputs}, allow_nan=False)
    if len(payload) > 140000:
        raise ValueError("Execution input too large")
    worker = Path(
        os.environ.get(
            "WORKFLOW_WORKER_PATH",
            str(Path(__file__).with_name("safe_worker.py").resolve()),
        )
    )
    identity = {}
    raw_uid = os.environ.get("WORKFLOW_AGENT_UID")
    if raw_uid is not None:
        uid = int(raw_uid)
        if uid < 1000:
            raise ValueError("Agent worker must use a nonprivileged UID")
        identity = {"user": uid, "group": uid, "extra_groups": []}
    with tempfile.TemporaryDirectory(prefix="workflow-program-") as work:
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-S", str(worker)],
                input=payload,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=work,
                env={"PATH": "/usr/bin:/bin"},
                timeout=4,
                **identity,
            )
        except subprocess.TimeoutExpired:
            return {"error": "Execution exceeded its four-second wall limit"}
    if process.returncode != 0:
        return {"error": "Worker exceeded a resource limit or exited unsuccessfully"}
    try:
        return json.loads(process.stdout)
    except (ValueError, TypeError):
        return {"error": "Worker returned invalid output"}


def language():
    return {
        "signature": "def compute(data): ...",
        "builtins": sorted(FUNCTIONS),
        "methods": sorted(METHODS),
        "restrictions": "Pure Python: local helper functions, bounded loops and recursion, conditionals, comprehensions, lambda sorting keys and collection operations. No imports, files, network, classes, private attributes or indirect calls. range <=5000; CPU <=2s; wall <=4s; memory <=256MiB.",
    }
