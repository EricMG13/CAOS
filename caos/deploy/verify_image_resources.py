import sys
from pathlib import Path

root = Path(__file__).resolve().parent
source_server = root.parent / "server"
if (source_server / "caos").is_dir():
    sys.path.insert(0, str(source_server))

from caos.methodology.bundle import DeployVBundle  # noqa: E402


bundle_root = root / "caos" / "methodology" / "vendor" / "deploy_v"
if not bundle_root.is_dir():
    bundle_root = root.parent / "server" / "caos" / "methodology" / "vendor" / "deploy_v"
report = DeployVBundle(bundle_root).verify()
assert report["checked"] == 307
assert report["mismatches"] == 0
print(report)
