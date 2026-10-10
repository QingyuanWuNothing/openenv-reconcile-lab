# Version 1: reward balance did not produce evaluation improvement

The completed v1 run solved **3/40 private tasks (7.5%)**, versus **4/40 (10%)** for the untrained reference: one fewer solved task. Industrial fell from 2/5 to 1/5; office remained 2/5. The other six domains scored zero in both results. This small, single-attempt evaluation does not identify a cause or establish systematic forgetting.

The [public dashboard](https://openenvarena-training.hf.space/?project=qingyuanwu&runs=eb2bf81abb27b075fe38da84) records 178 updates. Its mean training reward was **0.4883**, already close to 0.5. However, averaging concealed severe domain imbalance:

| Training family | Updates | Mean reward | Groups with zero reward variation |
|---|---:|---:|---:|
| Finance | 60 | 0.4375 | 11.7% |
| Science | 60 | 0.9222 | 63.3% |
| Office | 58 | 0.0920 | 32.8% |

Across the run, **36.0%** of groups had no reward variation. Nine task IDs used three domain labels, but all trained the same SQL investigation interface. Useful transfer requires varied actions and verification processes, not just labels and an aggregate reward target.

The dashboard's completion-clipped ratio averaged **0.9733**. That is an anomaly to investigate, not proof that almost all responses hit a token limit. Current TRL also classifies a completion by its final token; the Arena's implementation and truncation masking remain unverified. Board message 108 asks the organizers to clarify this.

The next iteration therefore uses eight distinct workflows, binary joint completion on fresh process artifacts, independent per-domain difficulty targets, identical-instance reward groups, coverage constraints, and untouched structural holdouts. A local trained-versus-base comparison must precede any claim of improved transfer. See the [eight-domain iteration plan](iteration-eight-domains.md) and [aggregate v1 evidence](v1-postmortem.json).
