"""003 trusted binding DTOs and native observations; no simulator or identity dependency."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ecs_ec.core.timezones import iana_zone


class Strict(BaseModel):
    """Reject unknown configuration and nonfinite numbers before deployment effects."""
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,frozen=True)


class Channel(Strict):
    """Explicit versioned native descriptor mapped to one already-provisioned001 source."""
    source_id: UUID
    category_id: str=Field(pattern=r'^CAT-0[1-7]$')
    device_local_id: str=Field(min_length=1,max_length=200)
    reduced_id: str=Field(min_length=1,max_length=200)
    device_name: str=Field(min_length=1,max_length=200)
    csv_topic_id: str=Field(min_length=1,max_length=200)
    json_value_item_id: str=Field(min_length=1,max_length=200)
    unit: Literal['Wh','kWh','MWh']='kWh'
    semantics: Literal['cumulative','interval']='cumulative'
    timestamp_role: Literal['reading_instant','interval_start','interval_end']='reading_instant'
    quantity: Literal['energy','unsupported']='energy'
    sampling_minutes: int=Field(default=15,gt=0,strict=True)
    provenance: Literal['synthetic','documented']='synthetic'
    evidence_ref: str=Field(default='synthetic:descriptor',min_length=1,max_length=300)
    checksum: str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def semantics_supported(self):
        """Require explicit evidence for noninitial sampling/interval descriptors, without claiming hardware fidelity."""
        if (self.semantics=='cumulative') != (self.timestamp_role=='reading_instant'):
            raise ValueError('incompatible_timestamp_role')
        if (self.sampling_minutes!=15 or self.semantics=='interval') and not self.checksum:
            raise ValueError('descriptor_evidence_required')
        return self


class BindingInput(Strict):
    """Immutable deployment-controlled identity, publisher and semantic source mapping; contains no credentials."""
    id: UUID
    revision: int=Field(gt=0,strict=True)
    building_id: UUID
    username: str=Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    directory: str=Field(default='/',pattern=r'^/(?:[a-zA-Z0-9_-]+/)*$')
    publisher_serial: str=Field(min_length=1,max_length=200)
    publisher_remote_id: str=Field(min_length=1,max_length=200)
    profile_id: Literal['pas600-doca0172en19-energy-v1']='pas600-doca0172en19-energy-v1'
    timezone: str
    enabled: bool=True
    channels: tuple[Channel,...]=Field(max_length=7)

    @model_validator(mode='after')
    def unique_sources(self):
        """Validate the zone and one-to-one mapping; no incoming filename can grant these identities."""
        iana_zone(self.timezone)
        for field in ('source_id','category_id','device_local_id','reduced_id','json_value_item_id'):
            if len({getattr(c,field) for c in self.channels})!=len(self.channels):
                raise ValueError('ambiguous_mapping')
        return self


@dataclass(frozen=True)
class Observation:
    """One immutable native cell/record, with nullable time/value and original quality/position evidence."""
    channel: str
    position: str
    instant: datetime|None
    value: Decimal|None
    token: str
    reason: str|None=None
    unit: str|None=None
    quality: str|None=None


@dataclass(frozen=True)
class NativeFile:
    """Parsed native envelope; publisher and device metadata remain untrusted until binding checks."""
    publisher: str
    readings: tuple[Observation,...]
    device_local_id: str|None=None
    device_name: str|None=None
    sampling_minutes: int|None=None


class ExportSelection(Strict):
    """Authorized explicit selection; no expected simulator values enter backend capture."""
    building_id:UUID
    category_ids:tuple[str,...]
    period:dict
    view:Literal['detail','hour','day','month','year']


class ConsumptionSnapshot(Strict):
    """Availability describes provider evidence, never whether the selected consumption equals zero."""
    status:Literal['available','unavailable']
    reason_code:str|None
    detail_results:list[dict]=Field(default_factory=list)
    aggregate_results:list[dict]=Field(default_factory=list)

    @model_validator(mode='after')
    def availability(self):
        """Unavailable captures require a cause and empty evidence lists; available requires no cause."""
        if (self.status=='available')!=(self.reason_code is None):raise ValueError('availability_reason')
        if self.status=='unavailable' and (self.detail_results or self.aggregate_results):raise ValueError('unavailable_has_data')
        return self


class AcquisitionExportSnapshot(Strict):
    """Versioned technical capture, not an endpoint or another consumption database."""
    schema_version:Literal[1]=1
    snapshot_id:UUID
    cutoff_at:datetime
    selection:ExportSelection
    publication:dict
    evaluations:list[dict]
    files:list[dict]
    readings:list[dict]
    candidates:list[dict]
    adaptations:list[dict]
    consumption_snapshot:ConsumptionSnapshot
