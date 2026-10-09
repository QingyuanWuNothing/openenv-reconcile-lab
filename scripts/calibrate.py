"""Collect strict-JSON target-model rollouts from a user-provided endpoint.

This is an approximate local calibration harness; the Arena's exact system
prompt is not published. It makes inference requests only when explicitly run.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reconcile_lab.environment import LabAction, ReconcileLab
from reconcile_lab.tasks import TASKS


def model_reply(endpoint, model, messages, thinking):
    payload = {"model": model, "messages": messages, "temperature": 1.0, "max_tokens": 4096, "chat_template_kwargs": {"enable_thinking": thinking}}
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("OPENAI_API_KEY")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        answer = json.load(response)
    return answer["choices"][0]["message"]["content"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True, help="OpenAI-compatible API base URL including /v1")
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--thinking", action="store_true")
    parser.add_argument("--output", default="reports/calibration.json")
    args = parser.parse_args()
    if args.episodes < 1:
        parser.error("--episodes must be positive")
    schema = LabAction.model_json_schema()
    system = "Act on the task using the supplied tools. Reply with exactly one JSON object matching this action schema, with no prose or markdown. You may end with {\"finish\":true}. Schema: " + json.dumps(schema)
    records = []
    for task in TASKS:
        for episode in range(args.episodes):
            env = ReconcileLab()
            obs = env.reset(task_id=task["task_id"], seed=10000 + episode)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": obs.model_dump_json(exclude={"reward", "done"})}]
            record = {"task_id": task["task_id"], "seed": 10000 + episode, "model": args.model, "thinking": args.thinking, "format_failure": False, "inference_failure": False}
            observed_characters = len(messages[-1]["content"])
            try:
                while not obs.done:
                    try:
                        reply = model_reply(args.endpoint, args.model, messages, args.thinking)
                    except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError):
                        record["inference_failure"] = True
                        break
                    try:
                        action = json.loads(reply)
                        if action == {"finish": True}:
                            parsed = LabAction(op="finish")
                        else:
                            # Arena reserves an action wrapper; use the same documented shape.
                            if isinstance(action, dict) and set(action) == {"action"} and isinstance(action["action"], dict):
                                action = action["action"]
                            parsed = LabAction.model_validate(action)
                    except (ValueError, TypeError):
                        record["format_failure"] = True
                        obs = env.step(LabAction(op="finish"))
                        break
                    obs = env.step(parsed)
                    serialized = obs.model_dump_json(exclude={"reward", "done"})
                    observed_characters += len(serialized)
                    messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": serialized}]
                record.update(reward=None if record["inference_failure"] else obs.reward, steps=env.state.step_count, observation_characters=observed_characters)
                records.append(record)
            finally:
                env.close()
            print(json.dumps(record), flush=True)
    summaries = []
    for task in TASKS:
        group = [r for r in records if r["task_id"] == task["task_id"]]
        rewards = [r["reward"] for r in group if r["reward"] is not None and math.isfinite(r["reward"])]
        summaries.append({"task_id": task["task_id"], "scored": len(rewards), "reward_mean": statistics.mean(rewards) if rewards else None, "reward_std": statistics.pstdev(rewards) if rewards else None, "full_success_rate": sum(r == 1 for r in rewards) / len(rewards) if rewards else None, "format_failures": sum(r["format_failure"] for r in group), "inference_failures": sum(r["inference_failure"] for r in group)})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"model": args.model, "thinking": args.thinking, "limitation": "Approximate prompt; no tokenizer-level Arena completion/context budget simulation.", "episodes": records, "summary": summaries}, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
