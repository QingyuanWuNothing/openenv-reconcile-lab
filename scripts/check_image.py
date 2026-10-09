"""Check a public GHCR image using anonymous access, with no saved credentials."""
import argparse
import json
import re
import urllib.parse
import urllib.request


def check(reference):
    match = re.fullmatch(r"ghcr\.io/([a-z0-9_.-]+/[a-z0-9_./-]+)@(sha256:[a-f0-9]{64})", reference)
    if not match:
        raise ValueError("Use a lowercase GHCR image reference pinned to a sha256 digest")
    name, digest = match.groups()
    query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{name}:pull"})
    # This token grants only an anonymous public pull; it remains in memory.
    with urllib.request.urlopen("https://ghcr.io/token?" + query, timeout=30) as response:
        token = json.load(response)["token"]
    headers = {"Authorization": "Bearer " + token, "Accept": "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"}
    request = urllib.request.Request(f"https://ghcr.io/v2/{name}/manifests/{digest}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        manifest = json.load(response)
        actual_digest = response.headers.get("Docker-Content-Digest")
    if actual_digest and actual_digest != digest:
        raise ValueError("Registry returned a different digest")
    layers = manifest["layers"]
    compressed = sum(layer["size"] for layer in layers)
    assert compressed <= 2 * 1024**3, compressed
    assert len(layers) <= 128, len(layers)
    config_request = urllib.request.Request(f"https://ghcr.io/v2/{name}/blobs/{manifest['config']['digest']}", headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(config_request, timeout=30) as response:
        config = json.load(response)
    assert config["os"] == "linux" and config["architecture"] == "amd64", config.get("architecture")
    return {"image": reference, "anonymous_pull": True, "compressed_bytes": compressed, "layers": len(layers), "os": config["os"], "architecture": config["architecture"], "command": config["config"].get("Cmd"), "ports": list(config["config"].get("ExposedPorts", {}))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    print(json.dumps(check(parser.parse_args().image), indent=2))
