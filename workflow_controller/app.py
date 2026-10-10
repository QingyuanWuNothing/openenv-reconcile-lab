import json
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .engine import Engine, revision

app = FastAPI(title="Reconcile Workflow Controller", docs_url=None, redoc_url=None)
engine = Engine()


class Reset(BaseModel):
    request_id: str = Field(max_length=80)
    task_id: str = Field(max_length=80)
    seed: int | None = None
    split: str = "train"
    mode: str = "training"
    revision: str = ""


class Step(BaseModel):
    seq: int = Field(ge=1)
    action: dict[str, Any]
    revision: str = ""


def check_revision(value):
    if value != revision():
        raise HTTPException(409, "Controller revision differs from the pinned contract")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "revision": revision(),
        "families": list(engine.curriculum.families),
    }


@app.get("/curriculum")
def curriculum():
    return {
        "revision": revision(),
        "cells": engine.curriculum.snapshot(),
        "optimization": engine.curriculum.optimization(),
    }


@app.post("/sessions")
def reset(body: Reset):
    check_revision(body.revision)
    try:
        return engine.reset(
            body.request_id, body.task_id, body.seed, body.split, body.mode
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from None


@app.post("/sessions/{session_id}/step")
def step(session_id: str, body: Step):
    check_revision(body.revision)
    if len(json.dumps(body.action, allow_nan=False)) > 16000:
        raise HTTPException(413, "Action too large")
    try:
        return engine.step(session_id, body.seq, body.action)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@app.delete("/sessions/{session_id}")
def close(session_id: str):
    engine.close(session_id)
    return {"closed": True}
