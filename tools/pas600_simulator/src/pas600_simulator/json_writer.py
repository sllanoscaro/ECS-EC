"""CewsMessage native Decimal JSON; all times use UTC plus integer milliseconds."""
from datetime import UTC
import simplejson


def utc_text(instant):
    """Encode an aware UTC instant with milliseconds and explicit Z suffix."""
    return instant.astimezone(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def encode_json(scenario, publication_time, channels):
    """Encode multiple device series without quality flags or private properties."""
    from pas600_simulator.anomalies import FormatDefect
    series = []
    for meter, rows in channels:
        if not rows:
            continue
        base = rows[0][0]
        records = []
        for instant, value in rows:
            delta = instant - base
            milliseconds = (delta.days * 86400 + delta.seconds) * 1000 + delta.microseconds // 1000
            if isinstance(value, FormatDefect):
                if value.mode == 'date':
                    milliseconds = 'invalid-date'; value = value.original
                else:
                    value = 'invalid-value'
            records.append({'v': value, 't': milliseconds})
        series.append({'valueItemId': meter.json_value_item_id, 'timestamp': utc_text(base), 'records': records})
    document = {'$schema': 'ESX/EDM/Protocol/Specific/CloudMessaging/DeviceToCloud/Data/CewsMessage',
        'message': {'remoteId': scenario.publisher.publisher_remote_id, 'contentType': 'data', 'cewsVersion': '3.0.0',
            'timestamp': utc_text(publication_time), 'content': {'data': {'timeseries': series}}}}
    return simplejson.dumps(document, use_decimal=True, allow_nan=False, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
