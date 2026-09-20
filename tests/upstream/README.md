# Historical upstream tests

These unchanged tests were written for a proposed in-tree Home Assistant
integration (`homeassistant.components.owlet`, `tests.common`) and also import
removed API exceptions. They cannot run as custom-component tests without
rewriting their harness and assertions. Retained here for provenance/reference;
excluded explicitly by pytest.ini. Active replacement regression coverage is
in ../test_maintenance.py and uses the real HA custom-component harness, API
candidate, coordinator and Sock parser. No claim is made that these historical
tests pass.
