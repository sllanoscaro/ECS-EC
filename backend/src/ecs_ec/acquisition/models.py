"""003 PostgreSQL ledger; immutable bytes live in the persistent acquisition volume, without destructive cascades."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID,uuid4
from sqlalchemy import Boolean,CheckConstraint,DateTime,ForeignKey,ForeignKeyConstraint,Integer,Numeric,String,UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped,mapped_column
from ecs_ec.core.database import Base


class Evidence:
    """UUID identity and UTC calendar retention shared by acquisition-owned evidence only."""
    id:Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    recorded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    retain_until:Mapped[datetime]=mapped_column(DateTime(timezone=True))


class AcquisitionBinding(Base):
    """Versioned trusted binding snapshot; credentials remain in protected deployment files."""
    __tablename__='acquisition_binding'
    __table_args__=(CheckConstraint('revision>0',name='positive_revision'),)
    id:Mapped[UUID]=mapped_column(primary_key=True)
    revision:Mapped[int]=mapped_column(Integer,primary_key=True)
    building_id:Mapped[UUID]=mapped_column(ForeignKey('consumption_building.id',ondelete='RESTRICT'))
    username:Mapped[str]=mapped_column(String(80),index=True)
    enabled:Mapped[bool]=mapped_column(Boolean)
    data:Mapped[dict]=mapped_column(JSONB)
    recorded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    retain_until:Mapped[datetime]=mapped_column(DateTime(timezone=True))


class SftpSessionAttempt(Evidence,Base):
    """One SSH subsystem session; only an explicit clean EOF can seal its closed files."""
    __tablename__='acquisition_session'
    __table_args__=(ForeignKeyConstraint(['binding_id','binding_revision'],['acquisition_binding.id','acquisition_binding.revision'],ondelete='RESTRICT'),
        CheckConstraint("state IN ('receiving','sealed','aborted')",name='state'),
        CheckConstraint('ended_at IS NULL OR ended_at>=recorded_at',name='time_order'))
    binding_id:Mapped[UUID]=mapped_column()
    binding_revision:Mapped[int]=mapped_column(Integer)
    ended_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    state:Mapped[str]=mapped_column(String(20))
    reason:Mapped[str|None]=mapped_column(String(60))
    manifest:Mapped[list|None]=mapped_column(JSONB(none_as_null=True))
    publication_id:Mapped[UUID|None]=mapped_column(ForeignKey('acquisition_publication.id',ondelete='RESTRICT',use_alter=True,name='fk_acquisition_session_publication'))
    correlation_ref:Mapped[UUID]=mapped_column()


class ReceivedFile(Evidence,Base):
    """Session-owned native bytes with contiguous offsets and explicit CLOSE status."""
    __tablename__='acquisition_file'
    __table_args__=(UniqueConstraint('session_id','name'),CheckConstraint("state IN ('writing','closed','sealed','aborted')",name='state'),
        CheckConstraint("parse_status IN ('pending','parsed','unreadable')",name='parse_state'),CheckConstraint('size>=0 AND written_offset>=0',name='size'))
    session_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_session.id',ondelete='RESTRICT'))
    name:Mapped[str]=mapped_column(String(255))
    storage_key:Mapped[str]=mapped_column(String(100),unique=True)
    size:Mapped[int]=mapped_column(Integer,default=0)
    written_offset:Mapped[int]=mapped_column(Integer,default=0)
    sha256:Mapped[str|None]=mapped_column(String(64))
    explicit_close:Mapped[bool]=mapped_column(Boolean,default=False)
    state:Mapped[str]=mapped_column(String(20))
    parse_status:Mapped[str]=mapped_column(String(20),default='pending')
    reason:Mapped[str|None]=mapped_column(String(60))


class NativePublication(Evidence,Base):
    """Content identity compares the complete canonical manifest in addition to its digest."""
    __tablename__='acquisition_publication'
    __table_args__=(ForeignKeyConstraint(['binding_id','binding_revision'],['acquisition_binding.id','acquisition_binding.revision'],ondelete='RESTRICT'),
        UniqueConstraint('binding_id','binding_revision','manifest_digest'),
        CheckConstraint("state IN ('queued','processing','evaluated','partial_failure')",name='state'))
    binding_id:Mapped[UUID]=mapped_column()
    binding_revision:Mapped[int]=mapped_column(Integer)
    publication_ref:Mapped[str]=mapped_column(String(100),unique=True)
    publisher:Mapped[str]=mapped_column(String(200))
    profile_id:Mapped[str]=mapped_column(String(100))
    manifest:Mapped[list]=mapped_column(JSONB)
    manifest_digest:Mapped[str]=mapped_column(String(64))
    sealed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    state:Mapped[str]=mapped_column(String(30))


class PublicationEvaluation(Evidence,Base):
    """A sealed re-send creates a new evaluation; crash recovery keeps its frozen002 attempt and input."""
    __tablename__='acquisition_evaluation'
    __table_args__=(UniqueConstraint('session_id'),CheckConstraint("state IN ('pending','processing','completed','partial_failure')",name='state'),
        CheckConstraint('(attempt_id IS NULL AND input_schema_version IS NULL AND input_records IS NULL AND input_digest IS NULL) OR (attempt_id IS NOT NULL AND input_schema_version IS NOT NULL AND input_schema_version>0 AND input_records IS NOT NULL AND input_digest IS NOT NULL)',name='frozen_input'))
    publication_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_publication.id',ondelete='RESTRICT'),index=True)
    session_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_session.id',ondelete='RESTRICT'))
    correlation_ref:Mapped[UUID]=mapped_column()
    attempt_id:Mapped[UUID|None]=mapped_column(unique=True)
    input_schema_version:Mapped[int|None]=mapped_column(Integer)
    input_records:Mapped[list|None]=mapped_column(JSONB(none_as_null=True))
    input_digest:Mapped[str|None]=mapped_column(String(64))
    state:Mapped[str]=mapped_column(String(30))
    completed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    outcome:Mapped[dict|None]=mapped_column(JSONB(none_as_null=True))


class NativeReading(Evidence,Base):
    """Every observation is retained; only first valid evidence reserves the semantic canonical identity."""
    __tablename__='acquisition_reading'
    __table_args__=(ForeignKeyConstraint(['binding_id','binding_revision'],['acquisition_binding.id','acquisition_binding.revision'],ondelete='RESTRICT'),
        UniqueConstraint('file_id','channel','position'),CheckConstraint("state IN ('valid','invalid','conflict','reference_only')",name='state'))
    file_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_file.id',ondelete='RESTRICT'))
    binding_id:Mapped[UUID]=mapped_column()
    binding_revision:Mapped[int]=mapped_column(Integer)
    source_id:Mapped[UUID|None]=mapped_column(ForeignKey('consumption_source.id',ondelete='RESTRICT'))
    channel:Mapped[str]=mapped_column(String(200))
    position:Mapped[str]=mapped_column(String(80))
    instant:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    value:Mapped[Decimal|None]=mapped_column(Numeric())
    original:Mapped[dict]=mapped_column(JSONB)
    state:Mapped[str]=mapped_column(String(30))
    reason:Mapped[str|None]=mapped_column(String(60))
    canonical_key:Mapped[str|None]=mapped_column(String(64),unique=True)
    canonical_ref:Mapped[UUID|None]=mapped_column(ForeignKey('acquisition_reading.id',ondelete='RESTRICT'))


class IntervalCandidate(Evidence,Base):
    """Exact normalized source interval and original endpoint references; acceptance remains owned by002."""
    __tablename__='acquisition_candidate'
    __table_args__=(ForeignKeyConstraint(['binding_id','binding_revision'],['acquisition_binding.id','acquisition_binding.revision'],ondelete='RESTRICT'),UniqueConstraint('binding_id','binding_revision','source_id','start','end'),CheckConstraint('start<"end"',name='interval_order'))
    binding_id:Mapped[UUID]=mapped_column()
    binding_revision:Mapped[int]=mapped_column(Integer)
    source_id:Mapped[UUID]=mapped_column(ForeignKey('consumption_source.id',ondelete='RESTRICT'))
    category_id:Mapped[str]=mapped_column(String(6))
    start:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    end:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    energy:Mapped[Decimal]=mapped_column(Numeric())
    unit:Mapped[str]=mapped_column(String(10))
    first_reading_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_reading.id',ondelete='RESTRICT'))
    last_reading_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_reading.id',ondelete='RESTRICT'))
    evidence_ref:Mapped[str]=mapped_column(String(100),unique=True)


class AdaptationResult(Evidence,Base):
    """Safe file/record/interval diagnostics are distinct from transport status and002 classifications."""
    __tablename__='acquisition_adaptation'
    evaluation_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_evaluation.id',ondelete='RESTRICT'),index=True)
    file_id:Mapped[UUID]=mapped_column(ForeignKey('acquisition_file.id',ondelete='RESTRICT'))
    reading_id:Mapped[UUID|None]=mapped_column(ForeignKey('acquisition_reading.id',ondelete='RESTRICT'))
    candidate_id:Mapped[UUID|None]=mapped_column(ForeignKey('acquisition_candidate.id',ondelete='RESTRICT'))
    position:Mapped[str|None]=mapped_column(String(80))
    scope:Mapped[str]=mapped_column(String(20))
    status:Mapped[str]=mapped_column(String(40))
    reason:Mapped[str|None]=mapped_column(String(60))


# Evidence is calendar-protected even when a caller bypasses the application helper.
for _model in (AcquisitionBinding,SftpSessionAttempt,ReceivedFile,NativePublication,PublicationEvaluation,NativeReading,IntervalCandidate,AdaptationResult):
    _model.__table__.append_constraint(CheckConstraint('retain_until>recorded_at',name='retention'))
PublicationEvaluation.__table__.append_constraint(CheckConstraint("input_digest IS NULL OR input_digest ~ '^[a-f0-9]{64}$'",name='digest'))
PublicationEvaluation.__table__.append_constraint(CheckConstraint("input_records IS NULL OR jsonb_typeof(input_records)='array'",name='input_array'))
NativeReading.__table__.append_constraint(CheckConstraint("value IS NULL OR (value>=0 AND value NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric))",name='finite_value'))
IntervalCandidate.__table__.append_constraint(CheckConstraint("energy>=0 AND energy NOT IN ('NaN'::numeric,'Infinity'::numeric,'-Infinity'::numeric)",name='finite_energy'))
