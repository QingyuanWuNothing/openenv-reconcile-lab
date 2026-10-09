"""Exercise every task over the live native WebSocket protocol, without tokens."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconcile_lab.tasks import TASKS, audit_parameters, generate
from tests.oracle import oracle_sql
import websockets


async def replay(base_url):
    with urllib.request.urlopen(base_url + "/schema", timeout=10) as response:
        schema = json.load(response)
    results = []
    for task in TASKS:
        for seed in [0, 17, 53]:
            async with websockets.connect(base_url.replace("http", "ws", 1) + "/ws", max_size=1000000) as ws:
                await ws.send(json.dumps({"type": "reset", "data": {"task_id": task["task_id"], "seed": seed}}))
                reset = json.loads(await ws.recv())
                assert reset["type"] == "observation", reset
                sql = oracle_sql(task["family"], audit_parameters(generate(task["task_id"], seed)))
                await ws.send(json.dumps({"type": "step", "data": {"op": "query", "sql": sql}}))
                query = json.loads(await ws.recv())["data"]["observation"]["data"]
                report = dict(zip(query["columns"], query["rows"][0]))
                await ws.send(json.dumps({"type": "step", "data": {"op": "submit", "report": report}}))
                terminal = json.loads(await ws.recv())["data"]
                assert terminal["done"] and terminal["reward"] == 1.0, terminal
                results.append({"task_id": task["task_id"], "seed": seed, "reward": terminal["reward"]})
        # The actual universal admission sequence is allowed to receive zero reward.
        async with websockets.connect(base_url.replace("http", "ws", 1) + "/ws") as ws:
            await ws.send(json.dumps({"type": "reset", "data": {"task_id": task["task_id"]}}))
            await ws.recv()
            await ws.send(json.dumps({"type": "step", "data": {"op": "finish"}}))
            terminal = json.loads(await ws.recv())["data"]
            assert terminal["done"] and terminal["reward"] == 0.0
    print(json.dumps({"oracle_episodes": results, "admission_episodes": len(TASKS), "schema": {"action": schema["action"], "observation": schema["observation"]}}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    asyncio.run(replay(parser.parse_args().url.rstrip("/")))
