"""Open a short-lived image test endpoint; no credentials or task solutions."""

import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request


def main():
    with Path("/tmp/standalone-cloudflared.log").open("w") as log:
        process = subprocess.Popen(
            [
                "/tmp/standalone-cloudflared",
                "tunnel",
                "--url",
                "http://127.0.0.1:8000",
                "--no-autoupdate",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    Path("/tmp/standalone-cloudflared.pid").write_text(str(process.pid))
    for _ in range(120):
        text = Path("/tmp/standalone-cloudflared.log").read_text()
        match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
        if match:
            url = match.group(0)
            try:
                with urllib.request.urlopen(url + "/health", timeout=3) as r:
                    if r.status == 200:
                        output = Path("reports/runtime-endpoint")
                        output.mkdir(parents=True, exist_ok=True)
                        (output / "runtime-url.txt").write_text(url + "\n")
                        (output / "image-digest.txt").write_text(
                            Path("reports/image-digest.txt").read_text()
                        )
                        (output / "release-revision.txt").write_text(
                            Path("reports/release-revision.txt").read_text()
                        )
                        print(
                            json.dumps(
                                {"temporary_runtime_url": url, "duration_seconds": 360}
                            )
                        )
                        return
            except (OSError, TimeoutError):
                pass
        if process.poll() is not None:
            raise RuntimeError("Temporary runtime tunnel exited")
        time.sleep(1)
    process.terminate()
    raise RuntimeError("Temporary runtime endpoint did not become ready")


if __name__ == "__main__":
    main()
