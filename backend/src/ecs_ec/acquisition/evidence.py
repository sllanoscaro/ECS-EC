"""Authorized single-capture003 export over real001/002 providers; all writes happen after releasing the UoW."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID,uuid4
from pydantic import BaseModel
from sqlalchemy import select,text
from ecs_ec.acquisition.models import AcquisitionBinding,NativePublication,PublicationEvaluation,ReceivedFile,NativeReading,IntervalCandidate,AdaptationResult
from ecs_ec.acquisition.schemas import BindingInput,ExportSelection,ConsumptionSnapshot,AcquisitionExportSnapshot
from ecs_ec.consumption.catalog import CATEGORY_IDS
from ecs_ec.consumption.periods import resolve_period
from ecs_ec.consumption.queries import row_view,diagnostic_view,segment_view
from ecs_ec.core.unit_of_work import UnitOfWork


def json_value(value):
    """Encode typed producer evidence without float arithmetic, live ORM relationships or arbitrary objects."""
    if isinstance(value,BaseModel):return value.model_dump(mode='json')
    if isinstance(value,(UUID,Decimal)):return str(value)
    if isinstance(value,datetime):return value.isoformat()
    if isinstance(value,dict):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_value(v) for v in value]
    if value is None or type(value) in (str,int,bool):return value
    raise ValueError('unsupported_evidence_value')


def row_fields(row,*names):
    """Copy only declared technical evidence fields, never ORM state or deployment secrets."""
    return {name:json_value(getattr(row,name)) for name in names}


async def export_results(service,*,process,publication_ref,start,end,timezone,categories,view):
    """Capture authorized publication/results and consumption in one REPEATABLE READ transaction and fixed cutoff.

    Unknown providers are explicitly unavailable. SQL/capture failures propagate, so CLI
    cannot replace a valid export with an invented coherent snapshot. Unknown002 copies
    remain unknown until the durable003 recovery copies their confirmed result.
    """
    service.settings.authorize(process)
    if view not in ('detail','hour','day','month','year') or not categories or len(set(categories))!=len(categories) or not set(categories)<=set(CATEGORY_IDS):
        raise ValueError('invalid_export_selection')
    async with UnitOfWork(service.database.sessions) as uow:
        await uow.session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        publication=await uow.session.scalar(select(NativePublication).where(NativePublication.publication_ref==publication_ref))
        if publication is None:raise ValueError('publication_not_found')
        bindingrow=await uow.session.get(AcquisitionBinding,(publication.binding_id,publication.binding_revision))
        binding=BindingInput.model_validate(bindingrow.data)
        period=resolve_period(start,end,timezone,binding.timezone)
        cutoff=service.clock.now()
        selection=ExportSelection(building_id=binding.building_id,category_ids=tuple(categories),period=dict(start=start,end=end,timezone=timezone),view=view)
        evaluations=(await uow.session.scalars(select(PublicationEvaluation).where(PublicationEvaluation.publication_id==publication.id,
            PublicationEvaluation.recorded_at<=cutoff).order_by(PublicationEvaluation.recorded_at,PublicationEvaluation.id))).all()
        sessions=[e.session_id for e in evaluations]
        files=(await uow.session.scalars(select(ReceivedFile).where(ReceivedFile.session_id.in_(sessions)).order_by(ReceivedFile.name,ReceivedFile.id))).all()
        import hashlib
        for file in files:
            path=service.settings.storage/file.storage_key
            if not path.is_file() or path.is_symlink():raise ValueError('sealed_bytes_missing')
            data=path.read_bytes()
            if len(data)!=file.size or hashlib.sha256(data).hexdigest()!=file.sha256:raise ValueError('sealed_bytes_changed')
        readings=(await uow.session.scalars(select(NativeReading).where(NativeReading.file_id.in_([f.id for f in files]),NativeReading.recorded_at<=cutoff).order_by(NativeReading.file_id,NativeReading.position,NativeReading.id))).all()
        adaptations=(await uow.session.scalars(select(AdaptationResult).where(AdaptationResult.evaluation_id.in_([e.id for e in evaluations]),AdaptationResult.recorded_at<=cutoff).order_by(AdaptationResult.evaluation_id,AdaptationResult.file_id,AdaptationResult.position,AdaptationResult.id))).all()
        candidates=(await uow.session.scalars(select(IntervalCandidate).where(IntervalCandidate.id.in_([a.candidate_id for a in adaptations if a.candidate_id])))).all()
        snapshot=ConsumptionSnapshot(status='unavailable',reason_code='provider_unavailable')
        if service.consumption is not None:
            # The internal provider explicitly authorizes this process-owned UoW; no human role is inferred.
            captured=await service.consumption.read_report_snapshot(binding.building_id,period.start,period.end,view,cutoff,None,unit_of_work=uow)
            detail_results=[];aggregate_results=[]
            for item in captured['categories']:
                category=item['category']['id']
                if category not in categories:continue
                if view=='detail':
                    detail=item['detail']
                    detail_results.append(dict(category_id=category,rows=[json_value(row_view(row,timezone)) for row in detail.rows],
                        diagnostics=[json_value(diagnostic_view(d,timezone)) for d in detail.diagnostics],
                        crossing_record_ids=json_value(detail.crossing_record_ids),crossing_diagnostic_ids=json_value(detail.crossing_diagnostic_ids),
                        withdrawn_record_ids=json_value(detail.withdrawn_record_ids),
                        configuration_segments=[json_value(segment_view(s,timezone)) for s in item['provenance_segments']]))
                else:aggregate_results.append(json_value(item['aggregates']))
            snapshot=ConsumptionSnapshot(status='available',reason_code=None,detail_results=detail_results,aggregate_results=aggregate_results)
        return AcquisitionExportSnapshot(snapshot_id=uuid4(),cutoff_at=cutoff,selection=selection,
            publication=row_fields(publication,'id','binding_id','binding_revision','publication_ref','manifest','manifest_digest','profile_id','publisher','sealed_at','state'),
            evaluations=[row_fields(e,'id','session_id','attempt_id','correlation_ref','state','input_schema_version','input_digest','input_records','outcome','recorded_at','completed_at') for e in evaluations],
            files=[row_fields(f,'id','session_id','name','size','sha256','state','parse_status','reason') for f in files],
            readings=[row_fields(r,'id','file_id','source_id','channel','position','instant','value','original','state','reason','canonical_ref') for r in readings],
            candidates=[row_fields(c,'id','source_id','category_id','start','end','energy','unit','first_reading_id','last_reading_id','evidence_ref') for c in candidates],
            adaptations=[row_fields(a,'id','evaluation_id','file_id','reading_id','candidate_id','position','scope','status','reason') for a in adaptations],
            consumption_snapshot=snapshot).model_dump(mode='json')
