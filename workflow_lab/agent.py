"""Thin RPC client. The deployed image contains only this protocol layer."""

import json
import os
import time
import urllib.error
import urllib.request
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from .schemas import WorkflowAction, WorkflowObservation
from .task_ids import TRAIN_TASKS, CALIBRATION_TASKS


class WorkflowLab(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, base_url=None, revision=None):
        super().__init__()
        self.base_url = (
            base_url
            or os.environ.get(
                "WORKFLOW_CONTROLLER_URL",
                "https://qingyuanwu-reconcile-workflow-controller.hf.space",
            )
        ).rstrip("/")
        self.revision = revision or os.environ.get("WORKFLOW_CONTROLLER_REVISION", "")
        self._session = None
        self._state = State()
        self._seq = 0

    def _request(self, path, body=None, method=None):
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    return json.load(r)
            except urllib.error.HTTPError as exc:
                if exc.code not in [502, 503, 504, 429] or attempt == 2:
                    raise RuntimeError(
                        f"Controller request failed with HTTP {exc.code}"
                    ) from None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise RuntimeError(
                        "Controller unavailable; no fabricated reward was returned"
                    ) from None
            time.sleep(attempt + 1)

    def list_splits(self):
        return ["train", "calibration"]

    def list_tasks(self, split):
        if split not in ["train", "calibration"]:
            raise ValueError("Unknown split")
        return [
            dict(t, id=t["task_id"], index=i)
            for i, t in enumerate(
                TRAIN_TASKS if split == "train" else CALIBRATION_TASKS
            )
        ]

    def num_tasks(self, split):
        return len(self.list_tasks(split))

    def get_task(self, split, index):
        if index < 0:
            raise IndexError(index)
        return self.list_tasks(split)[index]

    def get_task_range(self, split, start=None, stop=None):
        return self.list_tasks(split)[start:stop]

    def reset(
        self,
        seed=None,
        episode_id=None,
        task_id=None,
        split="train",
        index=0,
        mode="training",
        variant="train",
        **kwargs,
    ):
        if not self.revision:
            raise RuntimeError("A pinned controller revision is required")
        self.close()
        selected = task_id or self.get_task(split, index)["task_id"]
        response = self._request(
            "/sessions",
            {
                "request_id": str(uuid4()),
                "task_id": selected,
                "seed": seed,
                "split": variant,
                "mode": mode,
                "revision": self.revision,
            },
        )
        self._session = response["session_id"]
        self._seq = 0
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        return WorkflowObservation(**response["observation"])

    def step(self, action: WorkflowAction, timeout_s=None, **kwargs):
        if self._session is None:
            raise RuntimeError("Reset before step")
        seq = self._seq + 1
        response = self._request(
            "/sessions/" + self._session + "/step",
            {"seq": seq, "action": action.model_dump(), "revision": self.revision},
        )
        self._seq = seq
        self._state.step_count = seq
        return WorkflowObservation(**response)

    @property
    def state(self):
        return self._state

    def close(self):
        if self._session:
            try:
                self._request("/sessions/" + self._session, method="DELETE")
            except RuntimeError:
                pass
            self._session = None
