"""OpenEnv protocol implementation with a bounded, read-only SQLite workspace."""

import json
import secrets
import sqlite3
from typing import Any, Literal
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field

from .tasks import TASKS, Case, audit_parameters, generate
from .verifier import grade


class LabAction(Action):
    op: Literal["describe", "query", "submit", "finish"] = Field(description="Inspect table schema, execute read-only SQL, submit the numeric report, or finish for zero reward.")
    sql: str = Field(default="", max_length=8000, description="SQLite SELECT or WITH query for op=query. At most 20 result rows are returned.")
    report: dict[str, Any] = Field(default_factory=dict, description="For op=submit: a JSON object of the numeric metrics named in the task brief.")


class LabObservation(Observation):
    instruction: str = ""
    task_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    steps_left: int = 24


class ReconcileLab(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self._state = State()
        self._db = None
        self._case: Case | None = None
        self._task_id = ""
        self._done = False
        self._reward = 0.0

    def list_splits(self):
        return ["train"]

    def list_tasks(self, split: str):
        if split != "train":
            raise ValueError("Unknown split")
        return [dict(t, id=t["task_id"], index=i) for i, t in enumerate(TASKS)]

    def num_tasks(self, split: str):
        return len(self.list_tasks(split))

    def get_task(self, split: str, index: int):
        if index < 0:
            raise IndexError(index)
        return self.list_tasks(split)[index]

    def get_task_range(self, split: str, start=None, stop=None):
        return self.list_tasks(split)[start:stop]

    def reset(self, seed=None, episode_id=None, task_id=None, split="train", index=0, **kwargs):
        # Some clients pass task selectors in a task object; support that public shape too.
        task = kwargs.get("task")
        if task_id is None and isinstance(task, dict):
            task_id = task.get("task_id", task.get("id"))
        self._task_id = task_id if task_id is not None else self.get_task(split, index)["task_id"]
        self._case = generate(self._task_id, secrets.randbits(63) if seed is None else seed)
        self.close()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 32768)
        self._db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8000)
        for table, columns in self._case.columns.items():
            definitions = ", ".join(f'"{name}" {kind}' for name, kind in columns.items())
            self._db.execute(f'CREATE TABLE "{table}" ({definitions})')
            placeholders = ",".join("?" for _ in columns)
            self._db.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', [tuple(row[c] for c in columns) for row in self._case.tables[table]])
        self._db.commit()
        self._db.execute("PRAGMA query_only=ON")
        self._db.set_authorizer(self._authorize)
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._done, self._reward = False, 0.0
        return LabObservation(
            instruction=self._case.instruction + ' Tools: describe; query (read-only SQLite); submit (report object); finish. Reply with exactly one JSON action, e.g. {"op":"describe"}. A submit ends the episode; three metrics have equal reward weight.',
            task_id=self._task_id,
            data={"tables": self._describe(), "metrics": self._case.metrics, "parameters": audit_parameters(self._case)},
            reward=0.0,
        )

    @staticmethod
    def _authorize(code, arg1, arg2, dbname, source):
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
        if code not in allowed:
            return sqlite3.SQLITE_DENY
        if code == sqlite3.SQLITE_READ and (arg1 or "").startswith("sqlite_"):
            return sqlite3.SQLITE_DENY
        if code == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in {"load_extension", "readfile", "writefile", "randomblob", "zeroblob"}:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _describe(self):
        return {name: {"columns": cols, "rows": len(self._case.tables[name])} for name, cols in self._case.columns.items()}

    def _query(self, sql):
        if not sql.strip():
            raise ValueError("Provide a SQL SELECT or WITH query")
        ticks = 0

        def progress():
            nonlocal ticks
            ticks += 1
            return ticks > 200  # At most ~200,000 VM instructions.

        self._db.set_progress_handler(progress, 1000)
        try:
            cursor = self._db.execute(sql)
            rows = cursor.fetchmany(21)
            data = {"columns": [d[0] for d in cursor.description], "rows": [list(row) for row in rows[:20]], "truncated": len(rows) > 20}
            if len(json.dumps(data, allow_nan=False)) > 10000:
                raise ValueError("Result too large; aggregate or request fewer columns")
            return data
        finally:
            self._db.set_progress_handler(None, 0)

    def step(self, action: LabAction, timeout_s=None, **kwargs):
        if self._case is None:
            raise RuntimeError("Reset before taking an action")
        if self._done:
            return self._observation({"status": "episode already ended"})
        self._state.step_count += 1
        data = {}
        try:
            if action.op == "describe":
                data = {"tables": self._describe()}
            elif action.op == "query":
                data = self._query(action.sql)
            elif action.op == "submit":
                self._reward, checks = grade(self._case, action.report)
                self._done = True
                # Feedback never reveals reference values and cannot be used for repeated guesses.
                data = {"status": "report graded", "correct_metrics": checks}
            else:
                self._done = True
                data = {"status": "finished without a report"}
        except (sqlite3.Error, ValueError, TypeError) as exc:
            data = {"error": str(exc)[:240]}
        if self._state.step_count >= 24 and not self._done:
            self._done = True
            data["status"] = "action limit reached"
        return self._observation(data)

    def _observation(self, data):
        return LabObservation(done=self._done, reward=self._reward, task_id=self._task_id, data=data, steps_left=max(0, 24 - self._state.step_count))

    @property
    def state(self):
        return self._state

    def close(self):
        if self._db is not None:
            self._db.close()
            self._db = None
