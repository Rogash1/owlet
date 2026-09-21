# Owlet Home Assistant integration — maintained continuation

This is Rogash1's independent continuation of
[ryanbdclark/owlet](https://github.com/ryanbdclark/owlet), preserving upstream history,
the [Apache-2.0 license](LICENSE), [NOTICE](NOTICE) and historical changelog.
The development branch is `maintenance/local-candidate`; candidate
**2026.9.20rc1 is experimental, not production-ready**. It is not an upstream or
Owlet-endorsed release. No maintained release asset has been published yet.

The integration depends on the separately maintained
[pyowletapi fork](https://github.com/Rogash1/pyowletapi/tree/maintenance/local-candidate).
Authentication/HTTP/parsing belong in that library; config flows, coordinators,
entities, migration and diagnostics belong here.

## What changed and why

- Adapt modern HA options, authentication failures and reauthentication flows.
- Persist rotating token snapshots even if setup subsequently fails.
- Migrate account identity to region plus normalized email with collision checks.
  Existing entry/device/entity IDs and user renames are retained; only new entries
  receive a regional entity namespace.
- Load/reload/unload multiple devices correctly with the maintained API wheel.
- Mark missing measurements unknown and stale V3 readings unavailable using
  timestamps; identical readings alone do not mean stale data.
- Add an allowlisted diagnostic response and a last-updated sensor; avoid raw
  account/device responses in diagnostics and errors.

See [CHANGELOG.md](CHANGELOG.md) for source commits/PR leads and
[SECURITY-REVIEW.md](SECURITY-REVIEW.md) for implemented safeguards and limitations.

## Tested compatibility

The installed API wheel passed **22 HA regressions** on Core **2026.9.3**, Python
**3.14.6**, aiohttp **3.14.3** and the matching custom-component test harness.
The earlier 21-test suite passed Core 2026.2.3 / Python 3.13.15. Metadata currently
sets HA 2026.2.3 as the minimum; versions between these baselines are not all tested.
API regressions separately passed 40 tests. All network responses were mocked.

**No live HAOS or Owlet hardware validation is claimed.** WSL local tests do not
reproduce HAOS native libraries or Core container replacement. Real token rotation,
long polling, V2 freshness and every hardware revision remain unverified.
The V3 threshold `max(120 seconds, 3 polling intervals)` is a conservative local
policy, not a manufacturer guarantee. New alarm acknowledgment, body-position,
recovery and camera features remain disabled/unimplemented. Existing base-station
switches issue explicit user commands; polling never acknowledges alarms.

## Installation status and dependency

Do not install this candidate into production yet. The prepared manifest pins the
maintained API fork's versioned HTTPS wheel URL plus SHA256. **The release asset
is not published yet**, so neither ordinary HACS installation nor that URL is
currently an installable release. It does not resolve through upstream PyPI.

The intended wheel is hosted under Rogash1/pyowletapi release 2026.9.20rc1; the
exact path and digest are in `custom_components/owlet/manifest.json`. The repository
exists and is verified; the asset URL is prepared for future publication, not
claimed downloadable. Verify the published asset and SHA256 before installation.

HA loads the manifest from persistent `/config/custom_components/owlet` and installs
requirements before setup. Manually injecting a wheel into an existing Core
container is not a persistent deployment strategy. Hosting, restart/cache behavior
and container replacement must be verified in an isolated HAOS instance before
production use. URL requirements can invoke the package manager at startup even
when the version is installed; availability of the asset/cache matters.

For an approved future isolated installation, obtain the reviewed integration
archive from [this fork's releases](https://github.com/Rogash1/owlet/releases), verify
its checksum, place its `custom_components/owlet` directory in the test HA config,
and restart that test instance. Add Owlet through Settings > Devices & Services
and enter credentials locally. Do not copy production credentials into tests.

## Local tests against the packaged API

Build the companion API wheel using its README, keeping the checkouts as sibling
`pyowletapi` and `owlet-ha` directories. From this repository:

```sh
uv venv .venv-target --python 3.14.6
uv pip install --python .venv-target/bin/python -r requirements-test-target.lock
uv pip install --python .venv-target/bin/python --no-deps ../pyowletapi/dist/pyowletapi-2026.9.20rc1-py3-none-any.whl
PYTHONPATH=. .venv-target/bin/python -m pytest -c pytest.ini tests/test_maintenance.py -q --timeout=20
```

Review the wheel's hash against its build/release checksum before installation.
The workspace-only requirements-local.txt records a historical local artifact
hash; it is not a public package index configuration. Historical upstream tests
under tests/upstream target an in-tree HA component and are excluded. No live
credentials are required by the replacement regressions.

## Migration and rollback

Upgrade existing entries in place; do not delete and re-add them. Migration changes
config-entry version 1 to 2 and account unique ID, but keeps the entry ID and
legacy entity/device identifiers. A synthetic real-registry/recorder test verifies
user-renamed entity IDs and old/new history continuity through two reloads.
Invalid, colliding or future-version entries are refused rather than merged.

Before any approved deployment, create and verify an encrypted pre-migration
backup covering config entries, entity/device registries, integration files and
recorder history (coordinate external databases separately). **Downgrading files
alone is unsafe:** the upstream version-1 flow may reject version-2 entries.
Rollback restores the pre-migration configuration and database together using
supported HA backup restore, without hand-editing `.storage`. Changes/history after
the backup are lost; rotated cloud tokens may require user-driven reauthentication.
No production backup, restart or deployment is authorized by these instructions.

## Attribution and support

Ryan Clark and upstream contributors created this integration. [NOTICE](NOTICE)
identifies adapted fork contributions; [CHANGELOG.md](CHANGELOG.md) retains prior
releases and maintained changes. Report bugs to [this fork](https://github.com/Rogash1/owlet/issues)
and use [SECURITY.md](SECURITY.md) for sensitive reports. This community effort is
best-effort and is not a substitute for primary monitoring.
