# Owlet Home Assistant integration

Independent maintenance fork of [ryanbdclark/owlet](https://github.com/ryanbdclark/owlet),
retaining its history, [Apache-2.0 license](LICENSE) and [NOTICE](NOTICE).
Development uses `maintenance/local-candidate`. Prereleases are experimental,
not production-ready or endorsed by Owlet. Authentication and device parsing
are provided by the companion [pyowletapi fork](https://github.com/Rogash1/pyowletapi).

## Changes and compatibility

Maintenance updates options/reauthentication flows, preserves rotating tokens,
handles multiple devices, guards config-entry migration, and exposes allowlisted
diagnostics. Missing measurements are unknown; stale V3 measurements are unavailable.
V3 freshness uses `max(120 seconds, 3 polling intervals)`, a conservative local
policy rather than a manufacturer guarantee. V2 freshness cannot be inferred
from unchanged measurements. See [CHANGELOG.md](CHANGELOG.md) for source references.

The 22 mocked regressions passed with Core 2026.9.3, Python 3.14.6 and aiohttp 3.14.3.
An earlier 21-test suite passed Core 2026.2.3 / Python 3.13.15, the advertised minimum
HA baseline. Intermediate versions are unverified. No live HAOS, cloud or Owlet
hardware validation is claimed. Camera, recovery/body-position features and alarm
acknowledgment are not implemented. Existing base-station switches send explicit
user commands; polling never acknowledges alarms. This is not a primary monitor.

## Installation and dependency

Use an isolated test instance first. Download a versioned archive and checksums
from [releases](https://github.com/Rogash1/owlet/releases). After verifying SHA256,
place `custom_components/owlet` in the test HA configuration directory and restart
that test instance. Add Owlet through Settings > Devices & Services; enter account
credentials locally, never in an issue or source file.

`custom_components/owlet/manifest.json` pins the maintained API wheel's published
HTTPS URL and SHA256. HA resolves it from the persistent integration manifest;
a manual pip install inside the Core container is insufficient for persistence.
HAOS restart, download-cache behavior and container replacement still require
isolated testing. GitHub asset availability matters even when a version is installed.

## Development

Build the companion API wheel following its README, with sibling `pyowletapi`
and `owlet-ha` checkouts. From this repository:

```sh
uv venv .venv-target --python 3.14.6
uv pip install --python .venv-target/bin/python -r requirements-test-target.lock
uv pip install --python .venv-target/bin/python --reinstall --no-deps ../pyowletapi/dist/pyowletapi-2026.9.20rc1-py3-none-any.whl
PYTHONPATH=. .venv-target/bin/python -m pytest -c pytest.ini tests/test_maintenance.py -q --timeout=20
python3 scripts/build_release.py
```

The test lock pins the exact target harness, not integration runtime dependencies.
Tests use synthetic responses and no live credentials. Historical upstream tests
in `tests/upstream` are retained for provenance and excluded from discovery.
The ZIP builder includes only tracked component files and public documentation;
it writes to ignored `dist/`. Local rebuilds must not replace published assets.

## Migration and rollback

Upgrade entries in place; do not delete and re-add them. Migration changes config
version 1 to 2 and qualifies account identity by region. Existing entry IDs,
device IDs, entity IDs and user renames remain unchanged; only new entries use
regional entity namespaces. Invalid, colliding or future-version entries are refused.
Synthetic registry/recorder tests cover history continuity through reloads.

Before deployment, verify an encrypted backup covering configuration, registries,
integration files and recorder history; coordinate external databases separately.
Downgrading files alone is unsafe because the older version-1 flow may reject
version-2 entries. Rollback restores pre-migration configuration and database
together through supported HA restore, without hand-editing `.storage`. Later
history is lost and rotated tokens can require reauthentication.

## Attribution and support

Ryan Clark and upstream contributors created this integration. [NOTICE](NOTICE)
and [CHANGELOG.md](CHANGELOG.md) retain adapted contributions and upstream releases.
Use [issues](https://github.com/Rogash1/owlet/issues) for bugs and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.
