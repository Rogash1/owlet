"""Build a deterministic ZIP from tracked integration files; never publish."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "custom_components/owlet/manifest.json").read_text())["version"]
tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
docs = {"LICENSE", "NOTICE", "README.md", "CHANGELOG.md", "SECURITY.md"}
files = sorted(p for p in tracked if p in docs or p.startswith("custom_components/owlet/"))
if any(".agent-local" in Path(p).parts or Path(p).suffix == ".pyc" for p in files):
    raise ValueError("Unexpected private/generated tracked file")
out = root / "dist"
out.mkdir(exist_ok=True)
archive = out / f"owlet-ha-{version}.zip"
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for name in files:
        info = zipfile.ZipInfo(name, (2026, 9, 20, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, (root / name).read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
print(f"{digest}  {archive.name}")
