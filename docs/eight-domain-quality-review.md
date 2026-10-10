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

Seventeen focused tests pass, including 80 scientific identifications derived only from measured evidence, independent symbolic certificate policies, and rejection of valid-looking exports with wrong timing. These validate correctness and reachability, not model learning. Frozen one-H200 job **1791522** is screening the six changed cells on 48 training and 24 structural-holdout responses before promotion.

A cost-aware selector is also staged. It optimizes mixed-group evidence plus entropy per estimated charged token, constrained to per-domain reward 0.5 and exploration floors. Equal domain quotas and eight-instance coverage blocks preserve diversity. Its cost inputs use training data only. Fresh paired comparisons will report macro domain target error and clean mixed groups per million charged tokens; GPU-hour totals include startup and interrupted allocations. These are signal-efficiency proxies until a local trained-versus-base experiment measures a learning gain.

The [aggregate review](eight-domain-quality-review.json) contains no traces, input seeds, reference policies or grading source. The [earlier completed baseline](eight-domain-baseline.md) and [roadmap](iteration-eight-domains.md) remain separate. No next official request has been sent. Stable hosting that keeps controller source private and anonymous expanded-image replay remain release gates; the exact final JSON still requires fresh human approval.
