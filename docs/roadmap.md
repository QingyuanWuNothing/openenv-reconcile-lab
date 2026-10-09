# OpenEnv Arena requirements and implementation roadmap

Build and validate a small procedural environment, measure whether its tasks give the fixed model useful reward variation, then use the daily submission slot. The first candidate is Reconcile Lab, covering transferable relational investigation skills in three domains. Expand task variety after measuring the first candidate's behavior.

## Current competition requirements

The [official agent guide](https://openenvarena-arena.hf.space/AGENTS.md), checked on 9 October 2026, is the implementation contract. The [organizer overview](https://huggingface.co/openenvarena) includes older packaging and scoring descriptions; use the live guide for API details.

| Requirement | Implementation consequence |
|---|---|
| Any HF account; no paid plan or participant-owned HF Space is needed | Authenticate locally; community Arena GPU runs are provided |
| Fixed Qwen/Qwen3.8-27B and GRPO; one H200 for at most four hours including setup and rollouts | Optimize fast resets, short observations and informative reward groups |
| OpenEnv revision `86a180ede21e044f7929b9a7783ad83aa67d83a3` | Pin the SDK and runtime dependencies; test that exact SDK |
| 1–50 task IDs; at least one train task | Start with nine task settings; filter after calibration |
| Public Docker Hub or GHCR images, `linux/amd64`; one shared schema | Use one small image and a shared relational workspace interface |
| At most 50 images, 2 GiB compressed per image, 128 layers per image, 32 GiB combined with shared layers counted once | Inspect the registry manifest; use one image |
| Self-contained startup; no injected secrets, files, volumes or variables | Generate inputs locally; listen on 0.0.0.0:8000; include CMD and EXPOSE |
| `/health` ready within 120 seconds; OpenEnv runtime validation passes | Test a fresh container on CPU before publishing |
| Sandbox has 2 vCPU, 16 GiB RAM, no GPU, outbound internet and about 44 GiB free disk | Keep all per-episode records in memory; avoid heavy task dependencies |
| Same 1–16 example actions must terminate every task with finite reward in [0,1] | Use a universal finish action; separately test full-reward solutions |
| Public ungated Hugging Face dataset is needed for score attribution and ranking, though optional for API acceptance | Publish task descriptors, data examples, source links and reward explanation |
| One accepted submission per HF account per rolling 24 hours | Complete all local and anonymous-image checks before using a slot |
| The API accepts image references and automatically queues admitted submissions | Show the exact JSON and wait for the user's go-ahead |
| Image digest is frozen at submission; later pushes to a tag do not update the run | Record and submit the validated digest; use new IDs for later versions |

Task defaults are not performance targets. Allowed task limits include reset 120–300 seconds, rollout at most 3,600 seconds, verifier at most 1,800 seconds, and reset + rollout + verifier at most 3,600 seconds. Tool calls are at most 120 seconds each, 1,024 per episode and 60 per minute. Completion and context budgets are each capped at 32,768 tokens. The completion budget also includes observations after reset. Reconcile Lab uses tighter tool, time and action budgets, with concise query results.

## Proposed milestone schedule

Implementation status on 9 October 2026: the nine-task environment and roadmap are published in [the source repository](https://github.com/QingyuanWuNothing/openenv-reconcile-lab). The [amd64 container build](https://github.com/QingyuanWuNothing/openenv-reconcile-lab/actions/runs/37969746046) passed 29 tests, pinned OpenEnv runtime validation, 27 full-reward episodes and nine terminal admission replays. The immutable image is anonymously accessible and approximately 166 MiB compressed. A fresh [anonymous-pull validation](https://github.com/QingyuanWuNothing/openenv-reconcile-lab/actions/runs/37970096011) passed all container checks. The [public ungated dataset](https://huggingface.co/datasets/qingyuanwu/reconcile-lab) is published at revision `16cd9d61e0354457c8fd191162e5b45ef24c4057`, and the introduction, validation milestone and calibration question are posted as message 87 on the Arena board. The exact request is prepared and awaiting user approval. Target-model calibration remains unmeasured; no submission or private evaluation has occurred.

This schedule assumes one contributor comfortable with Python, approximately 15–25 hours across one week, and available account access. Queue time and target-model access can extend it.

| Milestone | Suggested effort | Deliverable and exit criterion |
|---|---|---|
| 1. Establish the contract and accounts | 1–2 hours | Read guide and board; HF login works; build and public registry paths established; introduction posted |
| 2. Implement a vertical slice | 3–4 hours | One family can reset, inspect, query, submit and terminate; correct and wrong reports score differently |
| 3. Add variation and verifier checks | 4–6 hours | Three families and three levels; deterministic seeded replay; independent SQL recomputation; malformed, partial, timeout and isolation tests pass |
| 4. Validate actual packaging | 2–3 hours | Pinned SDK runtime validation; fresh amd64 image; anonymous digest pull; schema equality and every task replay; image size within limits |
| 5. Calibrate the fixed model | 3–5 hours plus inference | Strict arena-style JSON actions, actual target model and trainer-compatible thinking configuration; at least 8 fresh episodes per setting; format failures tracked separately |
| 6. Publish and review | 1–2 hours | Public ungated dataset; immutable image; public milestone with validation evidence; exact request ready for user approval |
| 7. Train and evaluate | Queue plus up to 4 hours of GPU time | Submit only after approval; monitor lifecycle and Trackio; wait for private evaluation; report domain scores and public links |
| 8. Iterate after results | 2–4 hours per iteration | Diagnose saturation, zero reward, parsing, observation budgets and slow groups; change one major factor per version; respect rolling quota |

## Calibration and reward design

Measure success rate, reward mean and standard deviation, JSON/action validity, steps, token use and episode latency. A provisional target is approximately 20–80% full success with mixed rewards in rollout groups, rather than uniformly perfect or uniformly zero outcomes. This band is a design heuristic, not an arena rule or a promise of improvement. Keep partial rewards tied to valid output fields.

Because the trainer launches five parallel episodes and trains on the first four valid terminal rewards, within-task variation matters. Difficulty differences across task IDs do not help if every candidate for a particular task receives the same reward. Use fresh instances and retain settings that show useful variation under the target model.

The public board reports that thinking configuration and JSON formatting have affected calibration. Treat those reports as participant observations. Use the actual model with the closest available trainer configuration; label quantized or smaller-model probes as proxies. Record inference failures separately from scored task failures. Avoid paid inference without an agreed budget.

## Submission checklist

- Read the current guide and latest board updates.
- All nine task IDs select correctly, including split/index reset.
- Fresh inputs vary; identical seeds reproduce the same inputs.
- Correct reports receive 1; wrong reports receive 0; partial reports receive the intended fractions.
- Reference reports, oracle SQL and test files are absent from the agent interface and runtime image.
- SQL cannot write, attach files, load extensions, inspect grading state or exhaust an unbounded query.
- Finish, malformed-query and action-limit paths produce bounded, finite behavior.
- OpenEnv runtime validation and schema equality pass on the actual image.
- Anonymous amd64 pull and every declared task's example actions pass on the pinned digest.
- Registry manifest confirms compressed size and layers; readiness is below 120 seconds.
- Dataset is public and ungated; its card explains data generation, actions, reward and limitations.
- Target-model calibration is measured, or its absence is explicitly presented as a submission risk.
- Exact submission JSON is shown to the user and affirmative approval is received.

## Interpreting results

The eight evaluation domains are software engineering, industrial and physical systems, natural science, office work, finance and economics, math and formal reasoning, cybersecurity, and media production. Their private tasks are not published. The current guide does not specify a competition closing date or prize schedule; confirm those with the organizers before planning around a deadline.

The live leaderboard retains each user's best score per domain across evaluated runs and averages those eight bests. Every run is evaluated in all domains even when its training tasks focus on three. This makes focused later experiments useful, while the tiny evaluation set makes individual changes noisy. Track per-run scores and the untrained reference separately from the accumulated leaderboard score.

Use the Arena API for lifecycle state and the returned Trackio dashboard link for training metrics. Rising training reward alone does not prove transfer. If rewards saturate quickly, add meaningful exceptions or harder instances; if all rewards remain zero, simplify or increase useful tool access; if JSON failures dominate, clarify the action format; if too few optimizer steps finish, reduce rollout length and observation size. Never claim private-task improvements until an evaluated result is available.
