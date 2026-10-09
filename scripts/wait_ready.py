import argparse
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8000")
args = parser.parse_args()
start = time.monotonic()
while time.monotonic() - start < 120:
    try:
        with urllib.request.urlopen(args.url.rstrip("/") + "/health", timeout=2) as response:
            if response.status == 200:
                print(f"Ready after {time.monotonic() - start:.2f} seconds")
                break
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(1)
else:
    raise SystemExit("Image failed to become ready within 120 seconds")
