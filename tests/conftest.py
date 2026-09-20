import pytest

@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_recorder_before_hass(request):
    """Initialize recorder database fixtures before the autouse HA fixture."""
    if 'recorder_mock' in request.fixturenames:
        request.getfixturevalue('async_test_recorder')
