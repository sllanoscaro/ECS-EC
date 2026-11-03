"""Independent synthetic reference files exercise native readers without importing simulator writers."""
from pathlib import Path
from decimal import Decimal
import pytest


def test_csv_reference_offsets_and_bad_cell():
    """Native100/104 are exact and invalid independent cells never become numeric zero."""
    from ecs_ec.acquisition.csv_reader import read_csv
    data=Path('specs/003-simulador-pas600-sftp/contracts/examples/csv/1_mb_iEM3150 CAT03_20260101003000000_1.csv').read_bytes()
    result=read_csv(data,'Etc/UTC')
    assert [r.value for r in result.readings]==[Decimal('100'),Decimal('104')]
    assert result.readings[1].instant.isoformat().startswith('2026-01-01T00:15:00')
    altered=data.replace(b'104',b'NaN')
    rows=read_csv(altered,'Etc/UTC').readings
    assert rows[1].value is None and rows[1].reason=='invalid_value'


def test_json_reference_quality_and_numeric_tokens():
    """JSON retains exact numbers and unsupported quality while rejecting duplicate object keys."""
    from ecs_ec.acquisition.json_reader import read_json
    data=Path('specs/003-simulador-pas600-sftp/contracts/examples/json/20260101003000000_1.json').read_bytes()
    result=read_json(data)
    assert [r.value for r in result.readings]==[Decimal('100'),Decimal('104')]
    bad=data.replace(b'"v": 104',b'"v":104,"s":true')
    assert read_json(bad).readings[-1].reason=='unsupported_quality'
    with pytest.raises(ValueError):read_json(b'{"message":1,"message":2}')


@pytest.mark.parametrize('variant',['lf','crlf','four_cells','error19','offset','dst'])
def test_csv_native_variants_and_dst(variant):
    """Presentation variants preserve4kWh; native errors and an IANA-incompatible offset remain invalid."""
    from ecs_ec.acquisition.csv_reader import read_csv
    data=Path('specs/003-simulador-pas600-sftp/contracts/examples/csv/1_mb_iEM3150 CAT03_20260101003000000_1.csv').read_bytes().replace(b'\r\n',b'\n')
    zone='Etc/UTC'
    if variant=='crlf':data=data.replace(b'\n',b'\r\n')
    if variant=='four_cells':data=data.replace(b'"","","","modbus:',b'"","","","","modbus:')
    if variant=='error19':data=data.replace(b'"0","0","2026-',b'"19","0","2026-')
    if variant=='offset':zone='America/Santiago'
    if variant=='dst':
        data=data.replace(b'"0","0","2026-',b'"0","-180","2026-');zone='America/Santiago'
    result=read_csv(data,zone)
    if variant in ('error19','offset'):
        assert all(r.value is None for r in result.readings)
    else:
        assert [r.value for r in result.readings]==[Decimal('100'),Decimal('104')]


@pytest.mark.parametrize('record,reason',[({'v':True,'t':0},'invalid_value'),({'v':'104','t':0},'invalid_value'),
    ({'v':104,'t':0.5},'invalid_timestamp'),({'v':104,'t':0,'s':False},'invalid_quality'),
    ({'v':104,'t':0,'s':True},'unsupported_quality'),({'v':104,'t':10**30},'invalid_timestamp')])
def test_json_record_types(record,reason):
    """Per-record invalid types and quality do not discard the independent valid reference."""
    import json
    from ecs_ec.acquisition.json_reader import read_json
    data=json.loads(Path('specs/003-simulador-pas600-sftp/contracts/examples/json/20260101003000000_1.json').read_bytes())
    data['message']['content']['data']['timeseries'][0]['records'][1]=record
    result=read_json(json.dumps(data).encode())
    assert result.readings[0].value==100
    assert result.readings[1].reason==reason and result.readings[1].value is None


def test_csv_sanitized_native_name_matches_explicit_descriptor():
    """Native filename escaping is presentation only; trusted metadata still matches the complete device descriptor."""
    from types import SimpleNamespace
    from ecs_ec.acquisition.mapping import resolve_channel
    channel=SimpleNamespace(csv_topic_id='energy',device_local_id='dev',device_name='Meter/A',sampling_minutes=15,unit='kWh',reduced_id='1_mb',quantity='energy')
    binding=SimpleNamespace(publisher_serial='gateway',channels=[channel])
    native=SimpleNamespace(publisher='gateway',device_local_id='dev',device_name='Meter/A',sampling_minutes=15)
    observation=SimpleNamespace(channel='energy',unit='kWh')
    assert resolve_channel(binding,native,observation,'1_mb_Meter~A_20260101003000000_1.csv')==(channel,None)
