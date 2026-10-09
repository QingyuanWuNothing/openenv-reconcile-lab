# Workflow Lab v2 proxy candidate

This branch publishes the thin OpenEnv RPC image for industrial recovery, access-policy repair, meeting dispatch and caption rendering. The separate controller generates tasks and verifies process outcomes. Its publication requires separate approval; live reset and full public-image replay are pending that deployment. The image COPY whitelist contains only the RPC package and runtime dependencies. No v2 generator, grader, reference solver or calibration trace is published in this branch or image.

A 144-episode bf16 Qwen3.8-27B H200 probe scored 83 full successes, with seven format failures and no inference/budget failures. Read the [iteration roadmap](docs/iteration-v2.md), [aggregate calibration](docs/workflow-v2-calibration.json), and [release status](docs/workflow-v2-release.json). Local native proxy replay passes every task; the image CI checks its contents, schema and pinned SDK endpoints. These are preflight and base-model measurements, not private-evaluation gains.

Task dataset: https://huggingface.co/datasets/qingyuanwu/reconcile-workflow-lab

The admitted v1 pilot remains on the main branch: https://github.com/QingyuanWuNothing/openenv-reconcile-lab/tree/main

No v2 Arena submission has been sent. The exact request will be shown for fresh approval after complete public deployment validation.
