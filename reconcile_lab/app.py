import os

from openenv.core.env_server.http_server import create_app
from .environment import LabAction, LabObservation, ReconcileLab

os.environ.setdefault("ENABLE_WEB_INTERFACE", "false")
app = create_app(ReconcileLab, LabAction, LabObservation, env_name="reconcile_lab", max_concurrent_envs=8)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
