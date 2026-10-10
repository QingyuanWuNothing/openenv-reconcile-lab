import copy
import hashlib
import json
from pathlib import Path
import random
import secrets
import threading
import time

from .curriculum import Curriculum
from .registry import SCENARIOS
from .probes import PROBES


def revision():
    h = hashlib.sha256()
    names = sorted(p.name for p in Path(__file__).parent.glob("*.py")) + [
        "calibration_priors.json"
    ]
    for name in names:
        h.update(name.encode())
        h.update((Path(__file__).parent / name).read_bytes())
    return h.hexdigest()


class Engine:
    def __init__(self, scenarios=None):
        self.scenarios = SCENARIOS if scenarios is None else scenarios
        calibration = json.loads(
            (Path(__file__).parent / "calibration_priors.json").read_text()
        )
        priors = calibration["cells"]
        priors = {f: levels for f, levels in priors.items() if f in self.scenarios}
        self.curriculum = Curriculum(
            self.scenarios,
            priors=priors,
            reward_mode="binary",
            group_priors={
                f: levels
                for f, levels in calibration.get("groups", {}).items()
                if f in self.scenarios
            },
        )
        self.sessions = {}
        self.requests = {}
        self.lock = threading.RLock()

    def reset(self, request_id, task_id, seed=None, split="train", mode="training"):
        if split not in ["train", "holdout"] or mode not in ["training", "calibration"]:
            raise ValueError("Unknown split or mode")
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 80:
            raise ValueError("Invalid reset request ID")
        with self.lock:
            if request_id in self.requests:
                session = self.sessions.get(self.requests[request_id])
                if session:
                    return {
                        "session_id": session["id"],
                        "observation": copy.deepcopy(session["initial"]),
                    }
            family, separator, variant = task_id.rpartition("-")
            available = (
                {**PROBES, **self.scenarios}
                if mode == "calibration"
                else self.scenarios
            )
            if (
                not separator
                or family not in available
                or variant not in ["adaptive", "l1", "l2", "l3"]
            ):
                raise ValueError("Unknown task_id")
            if family in PROBES and (variant == "adaptive" or split != "holdout"):
                raise ValueError(
                    "Unseen-domain probes are held-out fixed-level evaluations only"
                )
            if seed is not None and (
                not isinstance(seed, int) or isinstance(seed, bool) or seed < 0
            ):
                raise ValueError("Invalid seed")
            shared_instance = (
                seed is None
                and mode == "training"
                and split == "train"
                and variant == "adaptive"
            )
            # Overlapping unseeded rollouts receive independent mutable copies of
            # one instance. Without a documented Arena group ID, this is a lease
            # for comparability, never evidence that a particular four are a group.
            peer = next(
                (
                    s
                    for s in self.sessions.values()
                    if shared_instance
                    and s.get("shared_instance")
                    and s["task_id"] == task_id
                    and not s["done"]
                    and time.monotonic() - s["created"] < 1800
                ),
                None,
            )
            seed = (
                peer["case_seed"]
                if peer
                else (secrets.randbits(63) if seed is None else seed)
            )
            rng = random.Random(seed)
            level = (
                peer["level"]
                if peer
                else (
                    (
                        self.curriculum.choose_balanced(family, rng)
                        if shared_instance
                        else self.curriculum.choose(family, rng)
                    )
                    if variant == "adaptive"
                    else int(variant[-1])
                )
            )
            case = available[family](seed, level, split)
            initial = {
                "instruction": case.instruction
                + ' Reply with one JSON action, for example {"op":"inspect","target":"'
                + list(case.resources)[0]
                + '"}. Use commit after producing and checking the requested outcome.',
                "task_id": task_id,
                "data": {
                    "resources": list(case.resources),
                    "tools": case.tools,
                    "difficulty": level,
                    "variant": split,
                    "budget": {"actions":32,"completion_and_feedback_tokens":8192,"context_tokens":16384},
                    "reward_rule": "1 only for a fresh process artifact satisfying every outcome constraint; otherwise 0.",
                },
                "steps_left": 32,
                "done": False,
                "reward": 0.0,
            }
            # Bound memory and discard expired episodes; closed episodes live briefly for retries.
            expired = [
                sid
                for sid, s in self.sessions.items()
                if time.monotonic() - s["created"] > 1800
            ]
            for sid in expired:
                self.requests.pop(self.sessions[sid]["request_id"], None)
                del self.sessions[sid]
            if len(self.sessions) >= 512:
                closed = next(
                    (sid for sid, s in self.sessions.items() if s["done"]), None
                )
                if closed is None:
                    raise RuntimeError("Controller capacity reached")
                self.requests.pop(self.sessions[closed]["request_id"], None)
                del self.sessions[closed]
            sid = secrets.token_urlsafe(32)
            session = {
                "id": sid,
                "request_id": request_id,
                "initial": initial,
                "case": case,
                "task_id": task_id,
                "family": family,
                "level": level,
                "case_seed": seed,
                "shared_instance": shared_instance,
                "learn": mode == "training"
                and split == "train"
                and variant == "adaptive",
                "done": False,
                "reward": 0.0,
                "seq": 0,
                "last": None,
                "created": time.monotonic(),
            }
            self.sessions[sid] = session
            self.requests[request_id] = sid
            return {"session_id": sid, "observation": copy.deepcopy(initial)}

    def step(self, session_id, seq, action):
        with self.lock:
            if session_id not in self.sessions:
                raise ValueError("Unknown or expired session")
            s = self.sessions[session_id]
            if seq == s["seq"] and s["last"] is not None:
                return copy.deepcopy(s["last"])
            if seq != s["seq"] + 1:
                raise ValueError("Out-of-order action sequence")
            if s["done"]:
                result = {
                    "task_id": s["task_id"],
                    "data": {"status": "episode already ended"},
                    "done": True,
                    "reward": s["reward"],
                    "steps_left": max(0, 32 - s["seq"]),
                }
                s["seq"] = seq
                s["last"] = result
                return copy.deepcopy(result)
            s["seq"] = seq
            case = s["case"]
            data = {}
            try:
                op = action.get("op")
                target = action.get("target", "")
                params = action.get("params", {})
                if (
                    op not in ["inspect", "patch", "run", "commit", "finish"]
                    or not isinstance(target, str)
                    or not isinstance(params, dict)
                    or len(json.dumps(action, allow_nan=False)) > 16000
                ):
                    raise ValueError("Malformed action")
                if op == "inspect":
                    data = {"resource": target, "content": case.inspect(target)}
                elif op == "patch":
                    data = case.patch(target, params)
                elif op == "run":
                    data = case.run(target, params)
                elif op == "commit":
                    s["reward"], checks = case.result()
                    s["done"] = True
                    data = {"status": "committed", "outcome_checks": checks}
                    if s["learn"]:
                        self.curriculum.observe(s["family"], s["level"], s["reward"])
                else:
                    s["done"] = True
                    data = {"status": "finished without commit"}
                    # A first-action finish is also used for Arena admission. Later
                    # finishes are failed multi-action attempts and provide evidence.
                    if s["learn"] and seq > 1:
                        self.curriculum.observe(s["family"], s["level"], 0.0)
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                data = {"error": str(exc)[:200]}
            if seq >= 32 and not s["done"]:
                s["done"] = True
                data["status"] = "action limit reached"
                if s["learn"]:
                    self.curriculum.observe(s["family"], s["level"], 0.0)
            result = {
                "instruction": "One JSON action. Use the listed tools; commit to grade completed work.",
                "task_id": s["task_id"],
                "data": data,
                "done": s["done"],
                "reward": s["reward"],
                "steps_left": max(0, 32 - seq),
            }
            s["last"] = result
            return copy.deepcopy(result)

    def close(self, session_id):
        with self.lock:
            s = self.sessions.pop(session_id, None)
            if s:
                self.requests.pop(s["request_id"], None)
