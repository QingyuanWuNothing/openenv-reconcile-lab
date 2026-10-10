# Reconcile Workflow Lab

Self-contained OpenEnv environment spanning repository repair, industrial recovery, scientific experiments, office scheduling, finance reconciliation, exact mathematical certificates, access-control repair and media editing.

Each task requires inspection, an intervention, execution and a fresh verification before committing. Reward is binary and checks the actual process outcome. Frozen task identifiers select the same instance across independent Arena containers. The final task bank is selected offline from training-only Qwen3.8-27B measurements, with equal domain quotas and difficulty coverage. Pilot measurement and final release links will be added after calibration.

The user authorized publication of runtime generator and verifier code. The image excludes reference solutions, author policies, tests, grading fixtures, model traces and credentials. The trusted server protects its files with root ownership; restricted agent programs execute as UID/GID 10001 without imports, files or network.

Build: `docker build --platform linux/amd64 -f Dockerfile.standalone --build-arg RELEASE_REVISION=$(python -c "from workflow_lab.task_bank import release_revision; print(release_revision())") -t reconcile-workflow-lab .`

OpenEnv SDK is pinned to the Arena revision in requirements.lock. This branch is a packaging candidate; no new official submission has been sent.
