from typing import Any, Literal
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class WorkflowAction(Action):
    op: Literal["inspect", "patch", "run", "commit", "finish"] = Field(
        description="Inspect inputs/state, change an artifact or setting, run a check/process, commit for terminal grading, or finish without committing."
    )
    target: str = Field(
        default="",
        max_length=80,
        description="Named resource or process from the task's tools description.",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments described by that tool, such as settings, rules, bookings or segments.",
    )


class WorkflowObservation(Observation):
    instruction: str = ""
    task_id: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    steps_left: int = 32
