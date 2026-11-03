"""Independent PAS600 CSV parser; conserve bytes externally and diagnose invalid cells without guessing energy."""
import csv
import io
from datetime import UTC,datetime,timedelta,timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from ecs_ec.acquisition.schemas import NativeFile,Observation

HEADERS=('Gateway Name','Gateway SN','Gateway IP Address','Gateway MAC Address','Device Name','Device Local ID','Device Type ID','Device Type Name','Logging Interval','Historical Intervals')


def read_csv(data:bytes,zone:str)->NativeFile:
    """Read the seven-row native preamble and both topic presentation variants; reject broken envelopes.

    Offset is checked against the deployment IANA zone. Invalid time/value/error cells
    produce observations with reasons; they never produce zero or hide independent cells.
    """
    try:
        rows=list(csv.reader(io.StringIO(data.decode('utf-8'),newline=''),strict=True))
        if len(rows)<7 or tuple(rows[0])!=HEADERS or len(rows[1])!=10 or rows[2] or rows[5]:
            raise ValueError()
        metadata=rows[1]
        sampling,count=int(metadata[8]),int(metadata[9])
        if sampling<=0 or count!=len(rows)-7 or rows[6][:3]!=['Error','UTC Offset (minutes)','Local Time Stamp']:
            raise ValueError()
        headings=rows[4]
        leading=next((i for i,v in enumerate(headings) if v),len(headings))
        if leading not in (3,4):raise ValueError()
        topics=headings[leading:]
        if len(topics)!=len(rows[6])-3 or not all(topics):raise ValueError()
    except (ValueError,UnicodeError,csv.Error,IndexError):
        raise ValueError('file_unreadable') from None
    output=[]
    for position,row in enumerate(rows[7:],8):
        instant,reason=None,None
        try:
            if len(row)!=len(topics)+3:raise ValueError()
            offset=int(row[1]); fixed=timezone(timedelta(minutes=offset))
            parsed=datetime.strptime(row[2],'%Y-%m-%d %H:%M:%S').replace(tzinfo=fixed)
            instant=parsed.astimezone(UTC)
            if instant.astimezone(ZoneInfo(zone)).utcoffset()!=parsed.utcoffset():raise ValueError()
        except (ValueError,IndexError,OverflowError):
            instant,reason=None,'invalid_timestamp'
        for col,topic in enumerate(topics,3):
            token=row[col] if col<len(row) else ''
            value=None;cause=reason
            try:
                if len(token)>16384:raise ValueError()
                value=Decimal(token)
                if not value.is_finite() or value<0 or abs(value.adjusted())>4096:raise ValueError()
            except (InvalidOperation,ValueError):
                value,cause=None,cause or 'invalid_value'
            if row[:1]!=['0']:
                value,cause=None,cause or 'native_error'
            if cause:value=None
            heading=rows[6][col]
            unit=heading.rsplit('(',1)[-1].rstrip(')') if '(' in heading else None
            output.append(Observation(topic,f'{position}:{col}',instant,value,token,cause,unit,row[0] if row else None))
    return NativeFile(metadata[1],tuple(output),metadata[5],metadata[4],sampling)
