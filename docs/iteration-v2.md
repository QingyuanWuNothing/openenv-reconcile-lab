# Iteration v2: behavioral workflows, learnability and diversity

This candidate is unsubmitted. The proxy image and visible task dataset can be
published under the existing authorization; live controller publication awaits
separate approval. Version 1 remains the admitted pilot:
[source](https://github.com/QingyuanWuNothing/openenv-reconcile-lab),
[dataset](https://huggingface.co/datasets/qingyuanwu/reconcile-lab), and
[training dashboard](https://openenvarena-training.hf.space/?project=qingyuanwu&runs=eb2bf81abb27b075fe38da84).
The v1 account slot ends on 10 October 2026 at 19:08:13 BST. No private evaluation
gain is available yet.

## What changes

The next candidate teaches an inspect → change → run → inspect → revise → commit
workflow. Every scored outcome requires a process artifact from the current
configuration. Patching after running invalidates the artifact. Forged reward
fields, an untouched workspace, and finish without commit earn zero. Partial
credit measures three explicit outcome predicates rather than tool-call counts.

| Family | Agentic work | Verified outcome | Diversity and transfer probes |
|---|---|---|---|
| Industrial | Diagnose low delivery, change bounded plant settings, run stress tests | Pressure and delivery recover; temperature remains safe | Fault combinations, coefficients and tighter operating bands; held-out coefficients |
| Cybersecurity | Inspect identities and requirements, replace an overbroad first-match ACL, replay requests | Required access preserved, unauthorized access blocked, writes restricted | Suspension, team boundaries, changing public-role permissions, classification/clearance, device trust and sealed resources; held-out team count |
| Office | Combine brief, rooms and busy calendars, book meetings, check conflicts, dispatch notifications | Feasible calendar, precedence, actual notifications matching bookings | Meeting count, duration, earliest/latest windows, attendee sets, room capacities and maintenance; held-out names and fresh constraints |
| Media | Inspect captions and production constraints, repair frames/text, render SRT | Valid timeline, preserved content and technically valid rendered asset | Caption count, word-budget compression, cue windows, repetition and overlap; held-out subjects and frame rates |

These are simulated workflows. Industrial and policy checks are executable
simulations, office dispatch creates actual notification records, and media
rendering serializes actual SRT text. They do not claim to reproduce the private
evaluation tasks or to establish generalization by themselves.

Version 1 already covers finance, science and office investigations. Later code
repair and executable math tasks remain planned. Adding domain labels alone is
not sufficient: each addition must introduce a useful action/inspection pattern,
pass independent verification, and exhibit measured reward variation.

## Sampling rule

The Arena chooses fixed task IDs in turn. Four adaptive training IDs therefore
preserve equal family representation. A shared external controller chooses one
of three difficulty levels *within* a family. Independent sandbox-local counters
would reset every episode and could not implement online adaptation.

For binary full success, reward variance is `p(1-p)`, which is largest at `p=0.5`.
For four independent training candidates, the probability of mixed full-success
outcomes is `L(p) = 1 - p^4 - (1-p)^4`. This motivates a learnability heuristic;
it does not guarantee the largest GRPO gradient. Partial rewards can vary even
when every candidate fails full success, so their distribution is recorded too.

Each family/level maintains a Beta(1,1) prior, discounts old evidence by 0.97 per
observation, and estimates full-success probability from terminal outcomes.
Because rewards are 0, 1/3, 2/3 or 1, the implementation also maintains a
discounted histogram. It uses `L_actual = 1 - sum(q_r^4)` over reward categories,
which reduces to the binary expression above and preserves learning signal when
partial outcomes differ even though every attempt fails full success. The weak
histogram prior has total mass two and full-success probability one half.
Weights are `0.75 * L_actual / sum(L_actual) + 0.25 / 3`. The 25% uniform exploration term
gives each level a minimum 8.33% weight. Family representation cannot collapse
toward whichever family is easiest to solve.

Calibration and held-out episodes do not update this state. A first-action
finish is excluded because the same action is used for Arena admission. Later
finishes and action-limit failures count as failures. Outcomes that never reach
the controller are unobserved; the resulting estimate is conditional on observed
attempts. Controller restart restores the measured eight-episode calibration
priors and clears subsequent online state. Calibration counts and online counts
are reported separately. The public
endpoint has no Arena-only authentication, so external callers could affect
observed rates. Treat adaptation as experimental and compare with a fixed
balanced curriculum before claiming benefit.

Different difficulty levels or instances within one GRPO group can add variance
unrelated to policy quality. Do not infer a shared optimizer group from request
timing. Board message 91 asks whether the Arena provides a group ID or shared
reset seed; a supported grouping identifier would allow a common difficulty and
instance for the five candidates, with independent session state.

## Calibration and release gates

Use the actual Qwen3.8-27B, bf16 on the authorized IridisX H200, with thinking off
and strict JSON replies. The staged model is pinned to
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. Local prompts and sampling settings
approximate the Arena; its exact prompt and model revision are not published.

1. Screen three fresh training episodes per setting to locate saturation and
   unscorable infrastructure failures. Three samples cannot establish a stable
   success rate.
2. Adjust settings based on observed error causes, then run at least eight fresh
   training and four held-out episodes per setting. Report full-success counts,
   partial-reward distributions, uncertainty, JSON failures and budget failures.
   Inference failures have no task score and are excluded from success estimates.
3. Keep settings with useful mixed outcomes and preserve workflow coverage. If
   every setting in a family saturates or fails, redesign that family before
   adding more task IDs. Do not optimize names, JSON quirks or a memorized solver.
4. Validate all declared task IDs over the actual OpenEnv WebSocket protocol and
   pass the pinned SDK runtime checks. Build an amd64 proxy image from a strict
   COPY whitelist; inspect it for absence of generators, verifiers, solutions,
   tests, calibration traces and credentials. The image has passed build and
   fresh anonymous-pull packaging, schema and six SDK endpoint checks.
5. Choose a stable controller host that keeps generation/grading source private.
   A protected HF Docker Space exposes the API while hiding its source. Current
   HF policy requires a paid plan to create Docker Spaces; this personal account
   is not PRO. The alternative is an existing HTTPS host. The earlier proposal
   to publish grading source publicly was rejected by automatic approval review
   for missing explicit authorization and exposure risk. No controller upload
   has run. Reference solvers and traces are excluded from the deployment bundle.
6. After approved deployment, test controller availability, anonymous image pull,
   immutable image digest, dataset visibility and every example action. Present
   the exact Arena submission request and obtain fresh approval before sending it.

## Local evidence

The workflow behavior suite currently passes 41 tests, including independent
solutions for 20 seeds × 12 settings × two splits (480 episodes), no-op/wrong
paths, forged reward, stale artifacts, HTTP revision pinning and idempotent
retries. The final native proxy replay passed 32 oracle episodes and four
terminal example episodes against the frozen controller with calibrated priors.
The complete local suite passes 70 tests. Full public-image outcome replay remains
pending the separately approved controller deployment.
Initial inference requests were unscored infrastructure failures. Colocation
exposed a missing CUDA compiler at the first token-sampling operation; enabling
the cluster CUDA module and a supported sampler fallback fixed inference. The
first usable screen scored all 36 episodes without inference failures: 34 full
successes and two prose/JSON format failures. Ten of twelve settings had three
full successes. This small sample suggests aggregate saturation, not stable
per-setting success estimates. The candidate was then strengthened with tighter
plant bands, conditional policy permissions, calendar windows/maintenance and
caption compression/cue windows. The larger probe completed 96 fresh training
and 48 held-out episodes: 83 full successes overall, seven format failures, no
budget or inference failures. The H200 is released automatically on completion.

| Family | Training full successes, levels 1 / 2 / 3 (each n=8) | Held-out full successes, levels 1 / 2 / 3 (each n=4) |
|---|---|---|
| Industrial | 7 / 5 / 2 | 2 / 2 / 1 |
| Cybersecurity | 7 / 4 / 2 | 2 / 3 / 0 |
| Office | 8 / 6 / 5 | 4 / 3 / 2 |
| Media | 8 / 2 / 2 | 4 / 0 / 2 |

Held-out security level 3 and media level 2 each earned exactly 2/3 credit in
all four attempts: both had zero reward variance despite partial credit. Office is comparatively
easier. Of five failed office training attempts, three were format failures.
Track JSON-valid conditional success alongside reward variation so formatting
does not masquerade as workflow difficulty. Eight/four samples yield wide
confidence intervals; the public summary includes Wilson 95% intervals. These
are base-model calibration probes, not evidence of training gain or private
evaluation performance.

The calibrated generation/grading revision is
`f77d6e9c366b0f5fb202fdca2d0d789ffc2a04fb432462ff496c9f1dd9c83098`.
The deployed candidate adds warm-start sampling priors without changing any
scenario or outcome check; its controller revision is recorded in
`workflow-v2-release.json`. Priors include training outcomes only. Held-out
outcomes never update the sampler. Industrial holdout uses four new load points;
office holdout uses a 15-minute grid and 45-minute meetings, cybersecurity has
more teams and higher classifications, and media uses unseen frame rates.

Before submission, freeze the controller fingerprint and image digest together.
A revision mismatch fails closed rather than silently training against changed
grading behavior. Availability is also a release requirement because each
episode relies on the external controller.

## Subsequent explicit-metric experiment

The new [metrics roadmap](metrics-roadmap.md) records an experimental binary
joint-completion candidate, constrained mean-target optimization and a fresh
IridisX comparison. This changes the reward rule and some holdout structures;
the public fractional-reward image above remains the earlier candidate. Its
measured results must not be presented as fresh evidence for the new revision.
