# A pooled reward of 0.5 can still fail the quality gate

IridisX job **1791356** completed 288 base-model responses on the frozen interface revision `2786332ca058b9ede39ffa8d361411324747f233bdd8828a6e06897d89c0959a` in **27 minutes 32 seconds**, with zero inference failures. Its training mean was **exactly 0.5**. That is not enough to accept the collection.

| Domain | Training reward | Reward given valid JSON | Clean mixed groups / complete clean groups |
|---|---:|---:|---:|
| Code | 0.500 | 0.600 | 1/2 |
| Industrial | 0.458 | 0.478 | 2/5 |
| Science, ambiguous input contract | 0.000 | 0.000 | 0/0 |
| Office | 0.750 | 0.783 | 1/5 |
| Finance | 0.500 | 0.500 | 2/6 |
| Math | 0.542 | 0.813 | 0/2 |
| Cybersecurity | 0.417 | 0.455 | 3/3 |
| Media | 0.833 | 1.000 | 0/4 |

There are 24 training responses per domain, grouped as four independent model attempts on each of six identical instances. Clean groups exclude every group with any formatting or budget failure. These small group counts have substantial uncertainty. Structural holdouts have only one independent instance per cell, so they cannot establish population-level transfer.

A missing science tool description caused genuine interface ambiguity: `compute(data)` receives `records` and `protocol`, while visible resources were called `measurements` and `protocol`. The omitted mapping was necessary information. Its zero rewards are diagnostic failures and will not fit the selector.

A separate explicit-contract science screen, **1791442**, completed 36 fresh responses in **11 minutes 9 seconds**. Training reward recovered to **0.625**, but valid-JSON reward was **0.9375**, formatting failed on **33.3%**, and both complete clean groups passed uniformly. Correcting the interface therefore exposed insufficient behavioral headroom. Neither profile is being represented as a successful GRPO training run.

Math's near-half reward also includes substantial formatting and budget failure. Media's valid-JSON attempts all succeeded. Neither has observed clean mixed-reward groups in this profile. Weighting those failures to create an overall mean of 0.5 would hide the problem.

The next focused designs move difficulty into actions and outcomes:

- **Science:** calibrate an instrument with measured controls, choose informative kinetic experiments, reproduce an assay, fit a mechanistic hypothesis and test its predictions. The harder level includes model selection for a Hill exponent. Structural holdouts change units and candidate kinetic constants.
- **Math:** choose active inequalities, use exact linear algebra and certify an integer optimum. The verifier checks primal feasibility, nonnegative multipliers, matched objective coefficients and a sound rounded lower bound. A feasible point without a valid optimality certificate fails.
- **Media:** follow a video edit list, drop partially cut words, convert source timing through playback speeds and frame rates, wrap retained content, and inspect a real subtitle export. A syntactically valid asset with incorrect cut alignment fails.

Seventeen focused tests pass, including 80 scientific identifications derived only from measured evidence, independent symbolic certificate policies, and rejection of valid-looking exports with wrong timing. These validate correctness and reachability, not model learning. Frozen one-H200 job **1791522** completed its 48 training and 24 structural-holdout responses in 11 minutes 40 seconds, with zero inference failures. **All 72 rewards were zero.** The redesigned tasks overshot the usable band and were not promoted. Trace replay on training cases showed no tool errors: scientific attempts ran out of budget while fitting parameters and omitted reproduction; mathematical attempts failed feasibility and certificate checks. Media attempts failed behavioral checks with no formatting or budget failures.

The bridge retained those outcome predicates while adding a numerical tool that fits only an agent-selected scientific model to its measured evidence, reports actual experimental progress, and simplifies the intermediate math and media levels. Job **1791730** completed 72 fresh responses in **10 minutes 6 seconds**. Training science reward was 9/16 (0.5625), but six attempts exhausted the rollout budget and the only complete clean group passed uniformly. Math and media were still all zero. This apparent scientific balance did not establish useful clean group variation.

Job **1792543** added exact arithmetic on agent-supplied numbers, a real edit-list assembly process and a smaller mathematical proof. It completed 72 responses in **9 minutes 44 seconds including cleanup**. Science passed 5/16 training responses; math and media remained zero. Private trace replay showed substantive failures: no math certificate proved the bound, and none of the 16 media episodes preserved all retained words. Only five of 48 submitted captions matched after ignoring case and punctuation, so cosmetic differences did not explain those failures. Tooling alone had not brought the tasks into band.

The next feedback screen, **1793278**, added numerical certificate diagnostics and chronological source-word previews. Neither tool chooses a reference answer: diagnostics compute the agent's proposed certificate, and a preview marks full/partial/outside words using the public source interval. The unchanged verifier still requires actual content, retimed boundaries and a real fresh export. It completed 72 responses in **9 minutes 57 seconds**, with no inference failures:

| Focused domain | Training reward | Complete clean mixed groups / clean groups | Budget failures / responses |
|---|---:|---:|---:|
| Science | 7/16 = 0.438 | 0/0 | 4/16 |
| Math | 0/16 = 0.000 | 0/2 | 2/16 |
| Media | 1/16 = 0.063 | 1/3 | 2/16 |

Development holdout rewards were science 2/8, math 0/8 and media 1/8. These are different seeds and different designs across screens, so their changes are not causal estimates of a tool benefit. The media success and clean mixed group are initial evidence of reachability for the base model; the tiny sample and low success rate still need improvement. A separate math-only screen, **1793462**, tests an exact solver for an agent-selected constraint basis. It returns continuous primal and dual equality solutions only; selection, integer feasibility, full multiplier order and a sound optimality bound remain the agent's work. It completed 24 responses in **6 minutes 30 seconds**, with zero inference failures: training reward **7/16 = 0.4375**, development holdout **1/8 = 0.125**. Training formatting failed on 2/16 and budget on 4/16. Its sole complete clean group passed uniformly; no clean mixed group was observed. Different seeds prevent a causal comparison to the earlier zero-reward variants. The numerical tool makes the workflow reachable for this model, but the profile is still rejected for training.

The full local suite passes **259 tests**; three additional targeted tests pass for the basis solver and exclusion of left-out domain priors. The feedback prototype completed **64 independently solved WebSocket episodes**, eight terminal admission checks and **eight independently solved pinned-SDK episodes** across all domains. Its separately pinned experimental contract is `bae60cc8d62338a3b2623d66a07ef4bdd3460ed69b86483700aa7e742263e1dd`. These checks establish correct execution and protocol behavior, not learnability.

A cost-aware selector is staged. It optimizes mixed-group evidence plus entropy per estimated charged token, constrained to per-domain reward 0.5 and exploration floors. Equal domain quotas and eight-instance coverage blocks preserve diversity. Its cost inputs use training data only. The local pilot now supports a matched uniform control, complete per-domain coverage blocks, clean-only empirical group evidence and paired held-out gain per training GPU hour, process GPU hour and million agent tokens. Independent motion-analysis and cash-ledger probes are excluded from training; leave-one-domain-out runs additionally test wholly unseen training domains. No pilot has passed the quality gate or measured a learning gain.

The [iteration scorecard](iteration-quality-scorecard.json) records aggregate outcomes and full allocation cost, including the rejected partial run. These completed screens consumed **2.684 allocated H200 hours**, including the interrupted allocation, and found **34 clean mixed training groups** in total. This cumulative total is an iteration-cost record across different designs, not a matched efficiency comparison. Calibration throughput is a signal-efficiency proxy; different designs across screens cannot establish an efficiency improvement. The baseline covers eight domains and 24 cells with equal quotas, but that measured diversity does not establish transfer. Final learning evaluation will use fresh sealed cases beyond the development holdouts used during iteration.

The [aggregate review](eight-domain-quality-review.json) contains no traces, input seeds, reference policies or grading source. The [earlier completed baseline](eight-domain-baseline.md) and [roadmap](iteration-eight-domains.md) remain separate. No next official request has been sent. Stable hosting that keeps controller source private and anonymous expanded-image replay remain release gates; the exact final JSON still requires fresh human approval.
