"""Independent exact CewsMessage reader; malformed envelopes differ from invalid record evidence."""
import json
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from ecs_ec.acquisition.schemas import NativeFile,Observation


def unique_object(pairs):
    """Reject ambiguous duplicate native fields rather than silently keeping the last value."""
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate_field')
        result[k]=v
    return result


def utc_instant(text):
    """Require a native aware UTC base time; no host timezone or naive fallback."""
    if not isinstance(text,str):raise ValueError('invalid_timestamp')
    result=datetime.fromisoformat(text)
    if result.utcoffset()!=timedelta(0):raise ValueError('invalid_timestamp')
    return result.astimezone(UTC)


def read_json(data:bytes)->NativeFile:
    """Parse numeric tokens as Decimal, preserve quality and record positions, never coerce strings/bools to energy."""
    try:
        root=json.loads(data,parse_float=Decimal,parse_int=Decimal,object_pairs_hook=unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('invalid_number')))
        if root['$schema']!='ESX/EDM/Protocol/Specific/CloudMessaging/DeviceToCloud/Data/CewsMessage':raise ValueError()
        msg=root['message']
        if msg['contentType']!='data' or msg['cewsVersion']!='3.0.0' or not isinstance(msg['remoteId'],str):raise ValueError()
        utc_instant(msg['timestamp'])
        series=msg['content']['data']['timeseries']
        if not isinstance(series,list):raise ValueError()
        for item in series:
            if not isinstance(item['valueItemId'],str) or not isinstance(item['records'],list):raise ValueError()
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise ValueError('file_unreadable') from None
    output=[]
    for i,item in enumerate(series):
        for j,record in enumerate(item['records']):
            instant,value,reason=None,None,None
            if not isinstance(record,dict):
                output.append(Observation(item['valueItemId'],f'{i}:{j}',None,None,'','invalid_record'));continue
            token=record.get('v')
            quality=record.get('s')
            try:
                offset=record['t']
                if type(offset) is not Decimal or not offset.is_finite() or abs(offset)>2**63-1 or offset!=offset.to_integral_value():raise ValueError()
                instant=utc_instant(item['timestamp'])+timedelta(milliseconds=int(offset))
            except (ValueError,KeyError,OverflowError,TypeError):reason='invalid_timestamp'
            if type(token) is not Decimal or not token.is_finite() or token<0 or abs(token.adjusted())>4096 or len(token.as_tuple().digits)>16384:
                reason=reason or 'invalid_value'
            else:value=token
            if 's' in record:reason=reason or ('invalid_quality' if quality is False else 'unsupported_quality')
            if reason:value=None
            output.append(Observation(item['valueItemId'],f'{i}:{j}',instant,value,str(token),reason,None,
                None if 's' not in record else str(quality)))
    return NativeFile(msg['remoteId'],tuple(output))
