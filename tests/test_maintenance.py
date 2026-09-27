from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import json

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pyowletapi.api import OwletAPI
from pyowletapi.sock import Sock
from pyowletapi.exceptions import OwletAuthenticationError, OwletConnectionError

from custom_components.owlet import async_migrate_entry
from custom_components.owlet.coordinator import OwletCoordinator
from custom_components.owlet.sensor import OwletSensor, SENSORS, OwletLastUpdatedSensor
from custom_components.owlet.binary_sensor import OwletAwakeSensor


def entry(hass, **kwargs):
    data={'region':'world','username':'synthetic@example.invalid','api_token':'synthetic',
          'expiry':9999999999,'refresh':'synthetic-refresh'}
    data.update(kwargs.pop('data', {}))
    obj=MockConfigEntry(domain='owlet', data=data, title='Synthetic',
                        unique_id=kwargs.pop('unique_id','synthetic@example.invalid'), **kwargs)
    obj.add_to_hass(hass)
    return obj


def sock():
    api=OwletAPI('world',session=AsyncMock())
    obj=Sock(api,{'dsn':'synthetic-device'})
    obj._version=3
    obj._properties={'heart_rate':120,'charging':False,
                     'last_updated':datetime.now(timezone.utc).isoformat()}
    return obj


async def test_migration_idempotent_preserves_data(hass):
    obj=entry(hass, version=1)
    old=dict(obj.data)
    assert await async_migrate_entry(hass,obj)
    assert obj.unique_id=='world_synthetic@example.invalid'
    assert obj.version==2 and obj.data==old
    assert await async_migrate_entry(hass,obj)
    assert obj.unique_id=='world_synthetic@example.invalid'


async def test_migration_collision_no_mutation(hass):
    obj=entry(hass,version=1)
    entry(hass,version=2,unique_id='world_synthetic@example.invalid')
    assert not await async_migrate_entry(hass,obj)
    assert obj.version==1


@pytest.mark.parametrize('data,version',[({'region':'invalid'},1),({'username':''},1),({},3)])
async def test_migration_rejects_invalid_or_future(hass,data,version):
    obj=entry(hass,data=data,version=version)
    assert not await async_migrate_entry(hass,obj)


async def test_coordinator_auth_no_email_key_and_persists_rotation(hass):
    obj=entry(hass)
    device=sock()
    device.api._refresh='rotated'
    device.update_properties=AsyncMock(side_effect=OwletAuthenticationError())
    coordinator=OwletCoordinator(hass,device,None,obj)
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    assert obj.data['refresh']=='rotated'


async def test_coordinator_connection_failure(hass):
    obj=entry(hass)
    device=sock()
    device.update_properties=AsyncMock(side_effect=OwletConnectionError())
    coordinator=OwletCoordinator(hass,device,5,obj)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_measurement_stale_missing_and_unchanged(hass):
    device=sock(); coordinator=OwletCoordinator(hass,device,5,entry(hass))
    sensor=OwletSensor(coordinator,next(s for s in SENSORS if s.key=='heart_rate'))
    assert sensor.available and sensor.native_value==120
    assert sensor.available  # equal readings are not stale evidence
    device._properties['last_updated']=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
    assert not sensor.available
    timestamp=OwletLastUpdatedSensor(coordinator)
    assert timestamp.available and timestamp.native_value.tzinfo is not None
    device._properties.pop('heart_rate')
    assert sensor.native_value is None and not sensor.available
    device._properties.pop('last_updated')
    assert not timestamp.available


async def test_unknown_sleep_not_awake(hass):
    device=sock();coordinator=OwletCoordinator(hass,device,5,entry(hass))
    sensor=OwletAwakeSensor(coordinator)
    assert sensor.is_on is None and not sensor.available


async def test_options_flow_modern(hass):
    obj=entry(hass,version=2)
    result=await hass.config_entries.options.async_init(obj.entry_id)
    assert result['type']=='form'
    with patch('custom_components.owlet.async_update_options',new=AsyncMock()):
        result=await hass.config_entries.options.async_configure(result['flow_id'],user_input={'scan_interval':15})
    assert result['type']=='create_entry'
    assert obj.options['scan_interval']==15


async def test_user_flow_region_and_api_candidate(hass):
    with patch('custom_components.owlet.config_flow.OwletAPI.authenticate',new=AsyncMock()), \
         patch('custom_components.owlet.config_flow.OwletAPI.get_devices',new=AsyncMock(return_value={})), \
         patch('custom_components.owlet.async_setup_entry',new=AsyncMock(return_value=True)):
        result=await hass.config_entries.flow.async_init('owlet',context={'source':SOURCE_USER})
        result=await hass.config_entries.flow.async_configure(result['flow_id'],user_input={
            'region':'europe','username':'Synthetic@example.invalid','password':'synthetic-password'})
        assert result['type']=='create_entry'
        assert result['result'].unique_id=='europe_synthetic@example.invalid'
        assert 'password' not in result['data']
        await hass.async_block_till_done()


@pytest.mark.parametrize("device_count", [1, 2])
async def test_setup_unload_real_sock_and_entities(hass, device_count):
    obj=entry(hass,version=2)
    raw={'REAL_TIME_VITALS':{'name':'REAL_TIME_VITALS','value':json.dumps({'hr':120,'ox':98,'bat':80,'chg':0,'bso':True,'ss':1}),
        'data_updated_at':datetime.now(timezone.utc).isoformat()}}
    with patch.object(OwletAPI,'get_devices',new=AsyncMock(return_value={'response':[{'device':{'dsn':f'synthetic-device-{n}'}} for n in range(device_count)]})), \
         patch.object(OwletAPI,'get_properties',new=AsyncMock(return_value={'response':raw})):
        assert await hass.config_entries.async_setup(obj.entry_id)
        await hass.async_block_till_done()
        assert obj.state==ConfigEntryState.LOADED
        assert sum(state.state=='120.0' for state in hass.states.async_all('sensor'))==device_count
        assert await hass.config_entries.async_reload(obj.entry_id)
        await hass.async_block_till_done()
        assert len(hass.data['owlet'][obj.entry_id])==device_count
        assert await hass.config_entries.async_unload(obj.entry_id)
        assert obj.entry_id not in hass.data['owlet']


@pytest.mark.parametrize('error,expected',[(OwletAuthenticationError(),'invalid_credentials'),(OwletConnectionError(),'cannot_connect')])
async def test_reauth_errors_visible(hass,error,expected):
    obj=entry(hass,version=2)
    with patch.object(OwletAPI,'authenticate',new=AsyncMock(side_effect=error)):
        result=await hass.config_entries.flow.async_init('owlet',context={'source':'reauth','entry_id':obj.entry_id},data=obj.data)
        result=await hass.config_entries.flow.async_configure(result['flow_id'],user_input={'password':'synthetic'})
        assert result['type']=='form'
        assert result['errors']['base']==expected


async def test_reauth_updates_and_reloads(hass):
    obj=entry(hass,version=2)
    tokens={'api_token':'rotated','expiry':9999999999,'refresh':'rotated-refresh'}
    with patch.object(OwletAPI,'authenticate',new=AsyncMock(return_value=tokens)), \
         patch.object(hass.config_entries,'async_reload',new=AsyncMock(return_value=True)) as reload:
        result=await hass.config_entries.flow.async_init('owlet',context={'source':'reauth','entry_id':obj.entry_id},data=obj.data)
        result=await hass.config_entries.flow.async_configure(result['flow_id'],user_input={'password':'synthetic'})
        assert result['type']=='abort' and result['reason']=='reauth_successful'
        assert obj.data['refresh']=='rotated-refresh'
        assert 'password' not in obj.data
        reload.assert_awaited_once_with(obj.entry_id)


async def test_setup_failure_persists_partial_rotation(hass):
    obj=entry(hass,version=2)
    async def fail(api, *args):
        api._refresh='rotated-on-failed-setup'
        raise OwletConnectionError()
    with patch.object(OwletAPI,'get_devices',new=fail):
        assert not await hass.config_entries.async_setup(obj.entry_id)
    assert obj.data['refresh']=='rotated-on-failed-setup'
    assert obj.state==ConfigEntryState.SETUP_RETRY
    await hass.config_entries.async_unload(obj.entry_id)


async def test_options_change_reloads_loaded_entry(hass):
    from custom_components.owlet import async_update_options
    obj=entry(hass,version=2)
    with patch.object(hass.config_entries,'async_reload',new=AsyncMock(return_value=True)) as reload:
        await async_update_options(hass,obj)
        reload.assert_awaited_once_with(obj.entry_id)


async def test_diagnostics_never_include_account_device_or_tokens(hass):
    from custom_components.owlet.diagnostics import async_get_config_entry_diagnostics
    obj=entry(hass,version=2)
    device=sock()
    hass.data['owlet']={obj.entry_id:{device.serial:OwletCoordinator(hass,device,5,obj)}}
    result=await async_get_config_entry_diagnostics(hass,obj)
    encoded=json.dumps(result)
    assert 'synthetic' not in encoded
    assert 'refresh' not in encoded
    assert 'username' not in encoded


async def test_manifest_matches_installed_candidate():
    from importlib.metadata import version
    from pathlib import Path
    manifest=json.loads((Path(__file__).parents[1]/'custom_components/owlet/manifest.json').read_text())
    from packaging.requirements import Requirement
    from urllib.parse import urlsplit, parse_qs
    import re
    assert len(manifest['requirements']) == 1
    raw_requirement = manifest['requirements'][0]
    assert not any(char.isspace() for char in raw_requirement)
    requirement = Requirement(raw_requirement)
    installed = version('pyowletapi')
    assert requirement.name == 'pyowletapi'
    assert manifest['version'] == installed
    url = urlsplit(requirement.url)
    assert url.scheme == 'https' and url.netloc == 'github.com'
    assert url.path == (f'/Rogash1/pyowletapi/releases/download/{installed}/'
                        f'pyowletapi-{installed}-py3-none-any.whl')
    assert not url.query and not url.username and not url.password
    hashes = parse_qs(url.fragment)
    assert set(hashes) == {'sha256'} and len(hashes['sha256']) == 1
    assert re.fullmatch(r'[0-9a-f]{64}', hashes['sha256'][0])


async def test_region_entity_namespace_preserves_legacy(hass):
    description=next(s for s in SENSORS if s.key=='heart_rate')
    def sensor(region, namespace=None):
        data={'region':region}
        if namespace:
            data['entity_namespace']=namespace
        obj=entry(hass,version=2,data=data,unique_id=region+'_'+str(namespace))
        return OwletSensor(OwletCoordinator(hass,sock(),5,obj),description)
    legacy=sensor('world')
    world=sensor('world','world')
    europe=sensor('europe','europe')
    assert legacy.unique_id=='synthetic-device-heart_rate'
    assert len({legacy.unique_id,world.unique_id,europe.unique_id})==3
    assert world.device_info['identifiers']!=europe.device_info['identifiers']


async def test_legacy_migration_preserves_registry_and_recorded_history(recorder_mock, hass):
    """Migrate a synthetic production-schema entry with a renamed entity and history."""
    from sqlalchemy import select
    from homeassistant.components.recorder.db_schema import States, StatesMeta
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    from pytest_homeassistant_custom_component.components.recorder.common import (
        async_recorder_block_till_done, async_trigger_db_commit,
    )

    obj = entry(hass, version=1, options={'scan_interval': 30})
    original_entry_id, original_data, original_options = obj.entry_id, dict(obj.data), dict(obj.options)
    devices, entities = dr.async_get(hass), er.async_get(hass)
    device = devices.async_get_or_create(config_entry_id=obj.entry_id,
                                        identifiers={('owlet', 'synthetic-device')})
    entity = entities.async_get_or_create('sensor', 'owlet', 'synthetic-device-heart_rate',
                                         config_entry=obj, device_id=device.id)
    entity = entities.async_update_entity(entity.entity_id, new_entity_id='sensor.user_chosen_pulse')
    await hass.async_start()
    hass.states.async_set(entity.entity_id, '111')
    await hass.async_block_till_done()
    async_trigger_db_commit(hass)
    await async_recorder_block_till_done(hass)

    def recorded():
        with recorder_mock.get_session() as session:
            return list(session.execute(select(States.state_id, States.metadata_id, States.state)
                .join(StatesMeta, States.metadata_id == StatesMeta.metadata_id)
                .where(StatesMeta.entity_id == entity.entity_id)))

    before = await hass.async_add_executor_job(recorded)
    assert any(row.state == '111' for row in before)
    # A Core restart clears live states but retains registry and recorder data.
    hass.states.async_remove(entity.entity_id)
    raw = {'REAL_TIME_VITALS': {'name': 'REAL_TIME_VITALS',
           'value': json.dumps({'hr': 120, 'ox': 98, 'bat': 80, 'chg': 0}),
           'data_updated_at': datetime.now(timezone.utc).isoformat()}}
    with patch.object(OwletAPI, 'get_devices', new=AsyncMock(return_value={
            'response': [{'device': {'dsn': 'synthetic-device'}}]})), \
         patch.object(OwletAPI, 'get_properties', new=AsyncMock(return_value={'response': raw})):
        assert await hass.config_entries.async_setup(obj.entry_id)
        await hass.async_block_till_done()
        assert obj.version == 2 and obj.unique_id == 'world_synthetic@example.invalid'
        assert obj.entry_id == original_entry_id
        assert dict(obj.data) == original_data and dict(obj.options) == original_options
        assert 'entity_namespace' not in obj.data
        for _ in range(2):
            current = entities.async_get(entity.entity_id)
            assert current.id == entity.id and current.unique_id == entity.unique_id
            assert current.device_id == device.id
            assert ('owlet', 'synthetic-device') in devices.async_get(device.id).identifiers
            assert hass.states.get(entity.entity_id).state == '120.0'
            assert await hass.config_entries.async_reload(obj.entry_id)
            await hass.async_block_till_done()
        async_trigger_db_commit(hass)
        await async_recorder_block_till_done(hass)
        after = await hass.async_add_executor_job(recorded)
        assert set(before).issubset(after)
        assert any(row.state == '120.0' for row in after)
        assert len({row.metadata_id for row in after}) == 1
        assert await hass.config_entries.async_unload(obj.entry_id)
