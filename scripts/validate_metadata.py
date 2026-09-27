"""Validate release metadata locally; optionally verify live GitHub settings."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def validate() -> dict:
    manifest = json.loads((ROOT / "custom_components/owlet/manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    requirements = manifest["requirements"]
    if len(requirements) != 1:
        raise ValueError("Expected one hash-pinned API requirement")
    requirement = requirements[0]
    if any(char.isspace() for char in requirement):
        raise ValueError("Manifest requirements must not contain whitespace (hassfest)")
    prefix = "pyowletapi@"
    if not requirement.startswith(prefix):
        raise ValueError("Expected a direct pyowletapi wheel requirement")
    url = urlsplit(requirement[len(prefix):])
    version = manifest["version"]
    expected_path = (f"/Rogash1/pyowletapi/releases/download/{version}/"
                     f"pyowletapi-{version}-py3-none-any.whl")
    if (url.scheme != "https" or url.netloc != "github.com"
            or url.path != expected_path or url.query
            or not re.fullmatch(r"sha256=[0-9a-f]{64}", url.fragment)):
        raise ValueError("Expected the versioned maintained HTTPS wheel and SHA256 pin")
    if not manifest.get("issue_tracker") or not hacs.get("homeassistant"):
        raise ValueError("Issue tracker and minimum Home Assistant version are required")
    return manifest


def check_github(manifest: dict, repository: str) -> None:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Expected an owner/repository name")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "owlet-metadata-validation"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/repos/{repository}", headers=headers)
    with urlopen(request, timeout=30) as response:
        metadata = json.load(response)
    if not metadata["has_issues"]:
        raise ValueError("Enable GitHub Issues; HACS requires a working issue tracker")
    if not metadata.get("topics"):
        raise ValueError("Add descriptive repository topics; HACS requires nonempty topics")
    if manifest["issue_tracker"] != metadata["html_url"] + "/issues":
        raise ValueError("Manifest issue_tracker does not match the validated repository")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-github", action="store_true")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "Rogash1/owlet"))
    args = parser.parse_args()
    try:
        manifest = validate()
        if args.check_github:
            check_github(manifest, args.repository)
    except HTTPError as error:
        parser.exit(1, f"GitHub metadata request failed (HTTP {error.code})\n")
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"Metadata validation failed: {error}\n")
    print("Metadata validation passed")
