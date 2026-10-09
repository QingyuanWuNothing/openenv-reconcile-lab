# Reconcile Lab for OpenEnv Arena

Reconcile Lab trains an agent to inspect relational data, translate a brief into rules, resolve record revisions, and submit a numerical report. It contains nine procedural task settings in finance, science, and office work. Every reset creates fresh synthetic data. One lightweight OpenEnv server serves all tasks with a shared action schema.

The competition fixes the model and training recipe. Our objective is to improve its performance on unfamiliar tasks by giving GRPO varied, verifiable outcomes. Correctness and protocol validation do not establish learning gain; target-model calibration and the private evaluation are separate milestones.

## Task families

| Family | Investigation | Three report fields |
|---|---|---|
| Finance | Reconcile invoices, latest payment revisions, refunds, dates, status and exchange rates | Total outstanding USD, northern-region outstanding USD, unpaid invoice count |
| Science | Apply batch QC and calibration, resolve reading revisions, balance unequal replicate counts | Treatment mean, control mean, eligible sample count |
| Office | Reconstruct ticket states and active intervals, account for pauses and reopening, apply priority SLAs | Open ticket count, breached open ticket count, total active minutes |

Each family has three levels. Higher levels increase records, revisions and exceptional cases. This is a proposed difficulty progression; calibration must measure which settings give the target model mixed outcomes.

## Interaction and rewards

Reset with `task_id` and an optional `seed`, or with `split="train"` and `index`. The first observation includes the brief, tables and column types, required metrics, and cutoff parameters. Actions are exactly one JSON object:

```json
{"op": "describe"}
{"op": "query", "sql": "SELECT COUNT(*) AS invoices FROM invoices"}
{"op": "submit", "report": {"outstanding_usd": 120.55, "north_outstanding_usd": 30.00, "unpaid_invoices": 2}}
{"op": "finish"}
```

Queries use read-only in-memory SQLite. They return at most 20 rows and bounded output, with a VM instruction limit. Submit ends the episode and awards one-third per correct metric. Monetary and mean fields have a 0.011 absolute tolerance; counts must match within 1e-9. Booleans, strings, missing fields and non-finite values do not earn credit. Finish or the 24-action limit ends an unfinished episode with zero reward. Reward does not depend on taking prescribed actions or matching a reference SQL string.

The independent Python verifier recomputes the result from the generated input records. Answers are never stored in the agent's tables. There is no shell or source-file reader among the actions. Independent SQL oracle queries exist only in the test harness, which is excluded from the container build context.

## Local development

Use Python 3.12 and the arena's exact OpenEnv revision, pinned in `pyproject.toml` and `requirements.lock`:

```sh
uv venv --python python3.12
uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/pytest -q
.venv/bin/ruff check reconcile_lab tests scripts
.venv/bin/python -m reconcile_lab.app
```

In a second terminal:

```sh
.venv/bin/openenv validate --url http://localhost:8000
.venv/bin/python scripts/replay.py --url http://localhost:8000
```

`replay.py` independently solves each task at three seeds over native WebSocket, then checks the universal admission action. Admission uses `{"op":"finish"}`: it demonstrates reliable terminal zero reward on every task. Separate oracle replays demonstrate solvability and positive reward.

## Build and publish

The first validated image is `ghcr.io/qingyuanwunothing/openenv-reconcile-lab@sha256:dd13c35036488a8ac6444a892095c1acdb225f03a783cc794f812b7e91811816`. It is anonymously accessible, with 173,872,395 compressed bytes and 10 layers. The [build and actual-image validation](https://github.com/QingyuanWuNothing/openenv-reconcile-lab/actions/runs/37969746046) passed the pinned SDK checks, 27 full-reward episodes and nine admission finish replays. [Independent anonymous validation](https://github.com/QingyuanWuNothing/openenv-reconcile-lab/actions/runs/37970096011) repeats these checks after pulling the immutable image on a fresh runner.

The GitHub Actions workflow tests the code, builds `linux/amd64`, validates and replays the actual image, and publishes it to GHCR. New GHCR packages default to private: change the package visibility to Public in GitHub package settings. Run the separate anonymous validation workflow afterwards. It removes registry authentication before pulling the image by its immutable digest, checks compressed image size, and repeats protocol validation and replay. No workflow submits an Arena request.

The Hugging Face dataset contains task descriptors, seeded input examples, and a card explaining the rewards. Generate it using `scripts/export_dataset.py`, then upload with your saved Hugging Face login. Tokens stay in the standard local login store or environment and are never embedded in the repository or request.

`scripts/hf_account.py identity`, `intro`, and `upload` use your saved login without exposing credentials. `intro` reads the board and posts the plan; `upload` publishes the generated dataset. These commands never submit an Arena request.

To calibrate against your own OpenAI-compatible inference endpoint, run `scripts/calibrate.py --endpoint http://localhost:8001/v1 --episodes 8`. The default target is Qwen/Qwen3.8-27B with thinking disabled; the guide does not publish the exact trainer prompt, so this harness is an approximation. It reports strict-format failures separately from inference failures and scored outcomes. It does not reproduce tokenizer-level Arena completion/context budgeting. Hosted inference may incur charges; use an endpoint and budget you have chosen.

## Submission and results

Prepare `submission.json` with `scripts/prepare_submission.py`, naming the anonymously validated image digest and public dataset. Review the complete request before submitting: admission automatically queues training and author-side admission failures consume the account's rolling 24-hour allowance. A submission uses one policy and up to four hours on one H200. The arena does not return trained weights.

Read [the current agent guide](https://openenvarena-arena.hf.space/AGENTS.md) before each submission. The image, API request and dataset workflow supersede the older overview's `submission.yaml` and 1–200 task wording. Use the current 1–50 limit.

The leaderboard ranks each user by the equally weighted average of their best result in each of eight domains across completed evaluations. Each evaluation has 40 private tasks, five per domain, with one attempt each. Training reward and run completion are separate from an evaluated score. Report per-domain results and uncertainty; with only five tasks per domain, one solved task changes that domain score by 20 percentage points.

See [the implementation roadmap](docs/roadmap.md) for milestones and launch gates.
