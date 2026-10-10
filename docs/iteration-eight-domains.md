# Eight-domain iteration: behavior, learnability and generalization

This is an **unsubmitted local candidate**. Version 1's completed private score fell from 4/40 for the reference to 3/40 after training; its aggregate training mean was nevertheless 0.4883. The [postmortem](v1-postmortem.md) motivates independent domain targets and broader action patterns.

## Implemented tasks

| Arena domain | Task behavior | Verified outcome | Untouched structural changes |
|---|---|---|---|
| Software engineering | Inspect a miniature repository, repair Python behavior, execute public and additional regression cases | Actual isolated program execution passes contract cases; source edited; fresh test artifact | New SKU counts, interval shapes, larger dependency graphs and missing dependencies |
| Industrial and physical systems | Diagnose sensor readings, change operating settings, run stress simulation | Pressure, delivery and temperature constraints all hold on the new simulation | Different load exponents and temperature relationships |
| Natural science | Write and execute an analysis, filter revised evidence, test a hypothesis, rerun with reordered records | Effect, eligible cohort and hypothesis agree with independent checks; reordered experiment reproduces results | New unit scales, site counts and cohort shapes |
| Office and white-collar work | Combine calendars, edit bookings incrementally, inspect conflicts, dispatch notifications | Every calendar constraint and dependency holds; actual notifications match final bookings | Larger calendars, new participants, capacities, time grid and day length |
| Finance and economics | Resolve revisions and settlement rules, post a journal, close balances | Complete eligible coverage; exact per-transaction FX rounding; closing balances agree with the records | Additional currencies, revision and transaction shapes |
| Math and formal reasoning | Apply exact rational row operations, classify a system, supply and verify a witness | Equivalence-preserving row reduction, justified classification and original-equation checks | Scaled/shuffled equations, dependent and inconsistent systems |
| Cybersecurity | Repair an overbroad access policy and replay a request matrix | Legitimate access preserved, unauthorized access denied, sensitive writes restricted | Additional teams and combined inactive/external identities |
| Media and content production | Edit caption timing and content, configure a renderer, inspect delivery | Actual SRT/WebVTT serialization matches requested format, FPS, timeline and content | Different format, frame rates, cue windows and content structure |

The tasks are original synthetic sandboxes. Physical recovery and request replay are simulations; Python programs, row operations, journal closing, notification dispatch and subtitle serialization execute real processes inside those sandboxes. They do not reproduce the private Arena evaluation.

There are **eight equally represented adaptive training IDs** and **24 fixed domain/difficulty cells**, below the Arena's 50-task limit. Agent programs execute in a restricted subprocess without access to controller state, grading functions, files or network. The public agent image contains only the OpenEnv protocol client. Author solutions, private regression inputs, graders and model traces remain outside public artifacts.

## Explicit optimization

| Objective | Measure | Selection and release rule |
|---|---|---|
| Per-domain learnability | Reward mean, distance from 0.5, valid-JSON conditional reward, instance-clustered uncertainty | Target 0.5 independently within every domain. Report unreachable targets; redesign those domains instead of averaging easy and hard domains together. |
| Useful GRPO signal | Fraction of four-response groups with mixed rewards; mean within-group variance; valid-JSON group analysis | Prefer genuine behavioral variation on one identical problem. A marginal 0.5 rate across different problems is insufficient. |
| Domain diversity | Observed counts and effective domain count | Fixed equal quotas: 12.5% per domain, effective count eight. |
| Task diversity | Level/cell entropy, effective cell count, public input-shape coverage and tool-transition coverage | At least 10% probability for every level within each domain; entropy weight 0.25. Finite-sample coverage is checked rather than assumed. |
| Generalization | Level-matched held-out outcomes by domain and trained-minus-base differences | Never use held-out outcomes to fit sampler weights. Domain labels, entropy and skill tags are design proxies, not demonstrated transfer. |
| Retention | Base versus locally trained behavior on untouched tasks | Investigate regressions before official submission. Cross-domain transfer needs a leave-one-domain-out experiment; training on all eight does not establish transfer to a wholly unseen domain. |

The selector combines discounted terminal-reward distributions with smoothed empirical same-instance mixed-group evidence when available. It optimizes each domain separately, preserving equal domain quotas and exploration floors. For binary reward, variance is largest at p=0.5; this is a useful heuristic, not a guarantee of maximal GRPO gradient or downstream gain.

Overlapping unseeded training sessions receive independent mutable copies of the same generated instance. Because the Arena has not documented a group identifier, this lease improves comparability but cannot certify that any particular four sessions form an optimizer group. Empirical four-response statistics are used only where the local experiment explicitly owns the grouping.

## Validation and H200 experiment

The local suite passes **155 tests**. Independent author policies completed all 24 cells on six seeds in each split (288 complete eight-domain episodes). All 64 declared fixed/adaptive task-and-split combinations passed solved WebSocket replay; eight terminal examples and eight pinned OpenEnv SDK client checks also passed. These validate reachability and protocol behavior, not model learnability.

IridisX job **1790983** is queued for one H200 using cached bf16 **Qwen3.8-27B**, pinned model revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, thinking disabled, temperature 1.0, 16,384-token context and 8,192 charged tokens per episode. Controller revision is `ffe22c3132f664a55e1e8bd053700d1b4587e4afe0f1b3fcbbc9ba473a22b85a`.

- Training calibration: 24 cells × four independent instances × four responses = **384 episodes**.
- Structural holdout baseline: 24 cells × two untouched instances × four responses = **192 episodes**.
- Priors and weights are fitted from training calibration only. Bootstrap intervals retain repeated responses together.
- Report per-domain and per-cell rewards, behavioral/format/budget failures, same-instance variation and observed diversity. Saturated or universally failing workflows require redesign.
- Next, validate frozen selection on fresh instances and run a local GRPO pilot with observations masked from the policy loss, then compare against the untouched base-model results. The local pilot approximates the Arena and cannot guarantee private-evaluation gains.

No new official request has been sent. Deployment still needs a stable HTTPS controller host that keeps grading source private, followed by anonymous public-image validation. A prior public-grader upload proposal was rejected by automatic approval review for source exposure and missing explicit authorization; no grading source was uploaded. The existing free HF account cannot currently create the selected protected Docker Space, so an existing HTTPS host is the preferred alternative. No subscription change is authorized or performed.

After measurement and deployment gates pass, present the exact submission JSON and wait for fresh approval before using the account's one accepted submission per rolling 24 hours.
