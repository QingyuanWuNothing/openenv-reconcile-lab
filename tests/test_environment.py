import json
import math

import pytest
from fastapi.testclient import TestClient
from jsonschema import validate

from reconcile_lab.app import app
from reconcile_lab.environment import LabAction, ReconcileLab
from reconcile_lab.tasks import TASKS, audit_parameters, generate
from reconcile_lab.verifier import expected_report, grade
from tests.oracle import oracle_sql


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["task_id"])
def test_independent_sql_matches_python_verifier(task):
    # Read actual agent-visible data and recompute independently in SQL.
    env = ReconcileLab()
    try:
        for seed in range(30):
            reset = env.reset(task_id=task["task_id"], seed=seed)
            sql = oracle_sql(task["family"], reset.data["parameters"])
            result = env.step(LabAction(op="query", sql=sql))
            assert "error" not in result.data
            report = dict(zip(result.data["columns"], result.data["rows"][0]))
            end = env.step(LabAction(op="submit", report=report))
            assert end.done and end.reward == 1.0, (task, seed, report, end)
    finally:
        env.close()


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["task_id"])
def test_reward_wrong_partial_and_terminal_paths(task):
    case = generate(task["task_id"], 51)
    report = expected_report(case)
    assert grade(case, {k: v + 100 for k, v in report.items()})[0] == 0
    for key in report:
        changed = dict(report)
        changed[key] += 1
        assert grade(case, changed)[0] == pytest.approx(2 / 3)
    assert grade(case, {})[0] == 0
    assert grade(case, {k: True for k in report})[0] == 0
    assert grade(case, {k: float("nan") for k in report})[0] == 0
    assert grade(case, {k: float("inf") for k in report})[0] == 0
    env = ReconcileLab()
    try:
        env.reset(task_id=task["task_id"], seed=51)
        end = env.step(LabAction(op="finish"))
        assert end.done and end.reward == 0
        assert env.step(LabAction(op="submit", report=report)).reward == 0
        env.reset(task_id=task["task_id"], seed=51)
        for _ in range(24):
            end = env.step(LabAction(op="describe"))
        assert end.done and end.reward == 0
    finally:
        env.close()


@pytest.mark.parametrize("sql", ["DELETE FROM invoices", "DROP TABLE invoices", "ATTACH DATABASE '/tmp/leak' AS other", "PRAGMA table_info(invoices)", "SELECT load_extension('x')", "SELECT * FROM sqlite_master", "SELECT randomblob(1000000)", "WITH RECURSIVE t(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM t) SELECT SUM(x) FROM t", "SELECT 1; SELECT 2;"])
def test_sql_cannot_mutate_or_escape(sql):
    env = ReconcileLab()
    try:
        env.reset(task_id="finance-l3", seed=3)
        result = env.step(LabAction(op="query", sql=sql))
        assert "error" in result.data
        result = env.step(LabAction(op="query", sql="SELECT COUNT(*) FROM invoices"))
        assert "error" not in result.data
    finally:
        env.close()


def test_reset_seed_and_session_isolation():
    a, b = ReconcileLab(), ReconcileLab()
    try:
        a.reset(task_id="finance-l3", seed=4)
        b.reset(task_id="science-l3", seed=4)
        first = json.dumps(a._case.tables, sort_keys=True)
        a.reset(task_id="finance-l3", seed=4)
        assert first == json.dumps(a._case.tables, sort_keys=True)
        a.reset(task_id="finance-l3", seed=5)
        assert first != json.dumps(a._case.tables, sort_keys=True)
        assert b.state.step_count == 0
        assert b.step(LabAction(op="query", sql="SELECT * FROM invoices")).data.get("error")
    finally:
        a.close()
        b.close()


def test_protocol_endpoints_task_api_and_native_websocket():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        schema = client.get("/schema").json()
        tasks = client.post("/reconcile_lab/tasks", json={"split": "train"}).json()["tasks"]
        assert len(tasks) == 9
        assert "expected" not in json.dumps(client.get("/state").json()).lower()
        for task in TASKS:
            with client.websocket_connect("/ws") as ws:
                ws.send_json({"type": "reset", "data": {"task_id": task["task_id"], "seed": 17}})
                reset = ws.receive_json()
                assert reset["type"] == "observation", reset
                observation = dict(reset["data"]["observation"], reward=reset["data"]["reward"], done=reset["data"]["done"])
                validate(observation, schema["observation"])
                sql = oracle_sql(task["family"], audit_parameters(generate(task["task_id"], 17)))
                ws.send_json({"type": "step", "data": {"op": "query", "sql": sql}})
                result = ws.receive_json()["data"]["observation"]["data"]
                report = dict(zip(result["columns"], result["rows"][0]))
                action = {"op": "submit", "report": report}
                validate(action, schema["action"])
                ws.send_json({"type": "step", "data": action})
                end = ws.receive_json()["data"]
                assert end["done"] and math.isfinite(end["reward"]) and end["reward"] == 1
