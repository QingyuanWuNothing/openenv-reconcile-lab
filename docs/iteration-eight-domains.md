# Eight-domain iteration: behavior, learnability and generalization

This is an **unsubmitted local candidate**. Version 1's completed private score fell from 4/40 for the reference to 3/40 after training; its aggregate training mean was nevertheless 0.4883. The [postmortem](v1-postmortem.md) motivates independent domain targets and broader action patterns.

## Implemented tasks

| Arena domain | Task behavior | Verified outcome | Untouched structural changes |
|---|---|---|---|
| Software engineering | Inspect a miniature repository, repair Python behavior and resource-constrained job batching, execute public and additional regression cases | Actual isolated program execution passes contract cases; source edited; fresh test artifact | New SKU counts, interval shapes, larger dependency graphs and missing dependencies |
| Industrial and physical systems | Diagnose sensor readings, change operating settings, run stress simulation | Pressure, delivery and temperature constraints all hold on the new simulation | Different load exponents and temperature relationships |
| Natural science | Write and execute an analysis, filter revised evidence, test a hypothesis with exact blocked randomization, rerun with reordered and controlled changes to evidence | Effect, eligible cohort, exact p-value and hypothesis agree with independent checks across evidence variants | New unit scales, site counts and cohort shapes |
| Office and white-collar work | Combine calendars, edit bookings incrementally, inspect conflicts, dispatch notifications | Every calendar constraint and dependency holds; actual notifications match final bookings | Larger calendars, new participants, capacities, time grid and day length |
| Finance and economics | Resolve revisions and settlement rules, post a journal, close balances | Complete eligible coverage; exact per-transaction FX rounding; closing balances agree with the records | Additional currencies, revision and transaction shapes |
| Math and formal reasoning | Apply and batch exact rational row operations on deeper systems, classify them, supply and verify a witness | Equivalence-preserving row reduction, justified classification and original-equation checks | Scaled/shuffled equations, dependent and inconsistent systems |
| Cybersecurity | Repair an overbroad access policy incrementally and replay a request matrix | Legitimate access preserved, unauthorized access denied, sensitive writes restricted | Additional teams and combined inactive/external identities |
| Media and content production | Edit captions incrementally, configure a renderer, inspect delivery | Actual SRT/WebVTT serialization matches requested format, FPS, timeline and content | Different format, frame rates, cue windows and content structure |

The tasks are original synthetic sandboxes. Physical recovery and request replay are simulations; Python programs, row operations, journal closing, notification dispatch and subtitle serialization execute real processes inside those sandboxes. They do not reproduce the private Arena evaluation.

There are **eight equally represented adaptive training IDs** and **24 fixed domain/difficulty cells**, below the Arena's 50-task limit. Agent programs execute in a restricted subprocess without access to controller state, grading functions, files or network. The public agent image contains only the OpenEnv protocol client. Author solutions, private regression inputs, graders and model traces remain outside public artifacts.

## Explicit optimization

| Objective | Measure | Selection and release rule |
|---|---|---|
| Per-domain learnability | Reward mean, distance from 0.5, valid-JSON conditional reward, instance-clustered uncertainty | Target 0.5 independently within every domain. Report unreachable targets; redesign those domains instead of averaging easy and hard domains together. |
| Useful GRPO signal | Fraction of four-response groups with mixed rewards; mean within-group variance; valid-JSON group analysis | Prefer genuine behavioral variation on one identical problem. A marginal 0.5 rate across different problems is insufficient. |
| Domain diversity | Observed counts and effective domain count | Fixed equal quotas: 12.5% per domain, effective count eight. |
| Task diversity | Level/cell entropy, effective cell count, public input-shape coverage and tool-transition coverage | Continuous weights have a 10% floor per level and entropy weight 0.25. A shuffled eight-instance live block guarantees at least one instance of each level; rounding and policy changes require fresh measurement. |
| Generalization | Level-matched held-out outcomes by domain and trained-minus-base differences | Never use held-out outcomes to fit sampler weights. Domain labels, entropy and skill tags are design proxies, not demonstrated transfer. |
| Retention | Base versus locally trained behavior on untouched tasks | Investigate regressions before official submission. Cross-domain transfer needs a leave-one-domain-out experiment; training on all eight does not establish transfer to a wholly unseen domain. |

The selector combines discounted terminal-reward distributions with smoothed empirical same-instance mixed-group evidence when available. It optimizes each domain separately, preserving equal domain quotas and exploration floors. For binary reward, variance is largest at p=0.5; this is a useful heuristic, not a guarantee of maximal GRPO gradient or downstream gain.

Overlapping unseeded training sessions receive independent mutable copies of the same generated instance. Because the Arena has not documented a group identifier, this lease improves comparability but cannot certify that any particular four sessions form an optimizer group. Empirical four-response statistics are used only where the local experiment explicitly owns the grouping.

## Validation and H200 experiment

The redesigned local suite passes **194 tests**. Independent author policies completed all 24 cells on six seeds in each split (288 complete eight-domain episodes). All 64 declared fixed/adaptive task-and-split combinations passed solved WebSocket replay; eight terminal examples and eight pinned OpenEnv SDK client checks also passed. These validate reachability and protocol behavior, not model learnability.

The first full calibration, IridisX job **1790983**, completed 576 base-model responses in 34 minutes 30 seconds with zero inference failures. Its mean training-distribution reward was **0.6432**, with mixed rewards in **42/96** identical-instance groups, or **24/66** among groups without format or budget failures. It covered all eight domains and all 24 cells, with effective counts of eight and 24. The [baseline report](eight-domain-baseline.md) distinguishes coverage, learnability, formatting and held-out capability.

Those measurements triggered further changes: harder code scheduling, exact randomization analysis, larger proof workflows, short incremental caption/policy edits and controlled scientific evidence variants. Submitted programs can use ordinary local helpers and bounded loops; attribute writes are rejected to prevent persistent state from carrying hidden regression inputs into public outputs. Hidden input text cannot appear in exception feedback.

Fresh calibration is now running as **1791163** on one H200. Its controller revision is `91e02e97c74efe4e9f13f7fbdfdf4499de5056f79f6d04a0c5b7a1c7567a33ff`. The cached bf16 Qwen3.8-27B model is pinned to `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; thinking is disabled, temperature is 1.0, context is 16,384 tokens and the episode allowance is 8,192 charged tokens.

- Training calibration: 24 cells × four independent instances × four responses = **384 episodes**, using new seeds.
- Structural holdout baseline: 24 cells × two untouched instances × four responses = **192 episodes**, kept out of sampler fitting.
- Reward counts include every scored training outcome. Empirical mixed-group priors use only complete groups without format/budget failures; overall and conditional rates are both reported.
- Validate frozen selection on fresh training instances before accepting a predicted 0.5. Inspect actual cell coverage and mixed behavioral rewards, not just an aggregate mean.
- A staged local LoRA GRPO pilot preserves sampled token IDs and masks observations from policy loss. It checks before/after behavior on matched sealed instances, with paired stratified uncertainty. Training is gated on usable variation, feasible per-domain targets and formatting quality.
- A leave-one-domain-out pilot is required to measure transfer to a wholly unseen domain. All-eight-domain training alone cannot establish that claim.

The redesigned candidate also passed all 64 fixed/adaptive task-and-split combinations through solved WebSocket replay, eight terminal examples and eight pinned SDK client checks. No redesigned-model performance or learned transfer gain is claimed while calibration is running.

No new official request has been sent. Deployment still needs a stable HTTPS controller host that keeps grading source private, followed by anonymous public-image validation. A prior public-grader upload proposal was rejected by automatic approval review for source exposure and missing explicit authorization; no grading source was uploaded. The existing free HF account cannot currently create the selected protected Docker Space, so an existing HTTPS host is the preferred alternative. No subscription change is authorized or performed.

After measurement and deployment gates pass, present the exact submission JSON and wait for fresh approval before using the account's one accepted submission per rolling 24 hours.
