"""CSV native profile writer; synthetic control identifiers never enter wire bytes."""
import csv
import io
from zoneinfo import ZoneInfo

HEADERS = ['Gateway Name', 'Gateway SN', 'Gateway IP Address', 'Gateway MAC Address', 'Device Name', 'Device Local ID', 'Device Type ID', 'Device Type Name', 'Logging Interval', 'Historical Intervals']


def encode_csv(scenario, meter, rows):
    """Serialize one device/frequency with seven preamble rows and quoted CRLF."""
    from pas600_simulator.anomalies import FormatDefect
    publisher = scenario.publisher
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
    writer.writerow(HEADERS)
    writer.writerow([publisher.name, publisher.publisher_serial, publisher.ip, publisher.mac, meter.device_name, meter.device_local_id, meter.device_type_id, meter.device_type_name, meter.sampling_minutes, len(rows)])
    writer.writerow([])
    writer.writerow(['', '', '', 'Topic ID1'])
    writer.writerow(['', '', '', meter.csv_topic_id])
    writer.writerow([])
    writer.writerow(['Error', 'UTC Offset (minutes)', 'Local Time Stamp', f'{meter.csv_measurement_name} ({meter.unit})'])
    for instant, value in rows:
        local = instant.astimezone(ZoneInfo(scenario.timezone))
        timestamp = local.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, FormatDefect):
            if value.mode == 'date':
                timestamp = 'invalid-date'; value = value.original
            else:
                value = 'invalid-value'
        writer.writerow(['0', int(local.utcoffset().total_seconds()) // 60, timestamp, str(value)])
    return stream.getvalue().encode('utf-8')
