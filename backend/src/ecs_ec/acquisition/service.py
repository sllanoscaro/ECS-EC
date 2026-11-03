"""003 durable adaptation and recoverable002 admission; no acquisition lock spans a reception call."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID,uuid4
from sqlalchemy import select
from ecs_ec.acquisition.models import (AcquisitionBinding,SftpSessionAttempt,ReceivedFile,NativePublication,
    PublicationEvaluation,NativeReading,IntervalCandidate,AdaptationResult)
from ecs_ec.acquisition.schemas import BindingInput
from ecs_ec.acquisition.csv_reader import read_csv
from ecs_ec.acquisition.json_reader import read_json
from ecs_ec.acquisition.mapping import resolve_channel
from ecs_ec.acquisition.counters import adjacent_delta
from ecs_ec.acquisition.store import binding_lock,digest
from ecs_ec.acquisition.audit import append_audit
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.retention import anniversary


class Acquisition:
    """In-process boundary for sealed batches, frozen evaluations and authorized export; reception remains002."""
    def __init__(self,database,clock,settings,reception,consumption=None,telemetry=None):
        """Inject installed providers; absent technical output never changes durable functional behavior."""
        self.database,self.clock,self.settings,self.reception=database,clock,settings,reception
        self.consumption,self.telemetry=consumption,telemetry

    def facts(self,zone):
        """Generate evidence timestamps and the platform-owned calendar anniversary, never365day retention."""
        now=self.clock.now()
        return dict(recorded_at=now,retain_until=anniversary(now,zone))

    def signal(self,handle,stage=None,outcome='success'):
        """Emit only fixed technical fields; failures and disabled output cannot escape to business transactions."""
        try:
            if self.telemetry:
                if stage:self.telemetry.stage(handle,stage,outcome=outcome)
                else:self.telemetry.complete(handle,outcome=outcome,code='ok' if outcome=='success' else 'processing_interrupted')
        except Exception:pass

    async def process_sealed(self,publication_id,evaluation_id=None):
        """Prepare under003 locks, release them, recover the same002 attempt, then atomically record its references."""
        handle=None;terminal='success'
        try:
            if self.telemetry:
                try:handle=self.telemetry.begin('acquisition.process','acquisition')
                except Exception:pass
            evaluation,binding,publication=await self.prepare(publication_id,evaluation_id,handle=handle)
            if evaluation.state=='completed':return evaluation.outcome
            if evaluation.attempt_id is None:return None
            self.signal(handle,'receive')
            process='process:acquisition:'+str(binding.id)
            lookup=await self.reception.read_attempt(evaluation.attempt_id,binding.building_id,process)
            if lookup.state=='completed':outcome=lookup.outcome
            else:
                outcome=await self.reception.accept(evaluation.attempt_id,binding.building_id,publication.publication_ref,
                    process,evaluation.input_records,'acquisition:'+evaluation.correlation_ref.hex)
            await self.finish(evaluation.id,binding,outcome)
            self.signal(handle,'publish')
            return outcome.model_dump(mode='json')
        except Exception:
            terminal='unexpected_error'
            raise
        finally:
            # Complete once even for no-record/already-completed captures; no reception terminal is synthesized.
            self.signal(handle,outcome=terminal)

    async def prepare(self,publication_id,evaluation_id=None,*,handle=None):
        """Freeze canonical ledger-derived input once; a second processor sees exactly the same attempt and records."""
        async with UnitOfWork(self.database.sessions) as uow:
            publication=await uow.session.get(NativePublication,publication_id)
            if publication is None:raise ValueError('publication_not_found')
            await binding_lock(uow,publication.binding_id)
            self.signal(handle,'claim')
            query=select(PublicationEvaluation).where(PublicationEvaluation.publication_id==publication_id)
            query=query.where(PublicationEvaluation.id==evaluation_id) if evaluation_id else query.order_by(PublicationEvaluation.recorded_at,PublicationEvaluation.id)
            evaluation=(await uow.session.scalars(query.with_for_update())).first()
            if evaluation is None:raise ValueError('evaluation_not_found')
            bindingrow=await uow.session.get(AcquisitionBinding,(publication.binding_id,publication.binding_revision))
            binding=BindingInput.model_validate(bindingrow.data)
            session=await uow.session.get(SftpSessionAttempt,evaluation.session_id)
            if session.state!='sealed':raise ValueError('unsealed_session')
            if evaluation.input_records is not None or evaluation.state=='completed':
                await uow.commit()
                return evaluation,binding,publication
            files=(await uow.session.scalars(select(ReceivedFile).where(ReceivedFile.session_id==session.id).order_by(ReceivedFile.name))).all()
            touched={}
            for file in files:
                observations=await self.ingest_file(uow,evaluation,binding,file)
                touched.update(observations)
            self.signal(handle,'parse')
            records=await self.candidates(uow,evaluation,binding,touched)
            self.signal(handle,'validate')
            evaluation.state='processing' if records else 'completed'
            publication.state='processing' if records else 'evaluated'
            if records:
                evaluation.attempt_id=uuid4();evaluation.input_schema_version=1
                evaluation.input_records=records;evaluation.input_digest=digest(records)
            else:
                evaluation.completed_at=self.clock.now()
                await append_audit(uow,self.clock,binding.timezone,'evaluated',evaluation.id)
            await uow.commit()
            return evaluation,binding,publication

    async def ingest_file(self,uow,evaluation,binding,file):
        """Preserve all native observations; only first valid content reserves a canonical source/time identity."""
        import hashlib
        path=self.settings.storage/file.storage_key
        if not path.is_file() or path.is_symlink():raise ValueError('sealed_bytes_missing')
        data=path.read_bytes()
        if len(data)!=file.size or hashlib.sha256(data).hexdigest()!=file.sha256:raise ValueError('sealed_bytes_changed')
        try:native=read_csv(data,binding.timezone) if file.name.endswith('.csv') else read_json(data)
        except ValueError:
            file.parse_status,file.reason='unreadable','file_unreadable'
            uow.session.add(AdaptationResult(evaluation_id=evaluation.id,file_id=file.id,scope='file',status='invalid',reason='file_unreadable',**self.facts(binding.timezone)))
            return {}
        file.parse_status='parsed'
        touched={}
        for observation in native.readings:
            channel,mismatch=resolve_channel(binding,native,observation,file.name)
            reason=mismatch or observation.reason
            row=NativeReading(id=uuid4(),file_id=file.id,binding_id=binding.id,binding_revision=binding.revision,
                source_id=channel.source_id if channel else None,channel=observation.channel[:200],position=observation.position,
                instant=observation.instant,value=observation.value,
                original=dict(channel=observation.channel,token=observation.token,unit=observation.unit,quality=observation.quality),
                state='invalid' if reason else 'valid',reason=reason,**self.facts(binding.timezone))
            if not reason:
                key=digest([str(binding.id),binding.revision,str(channel.source_id),observation.channel,observation.instant.isoformat()])
                existing=await uow.session.scalar(select(NativeReading).where(NativeReading.canonical_key==key))
                if existing:
                    row.canonical_ref=existing.id
                    if existing.value!=row.value:row.state,row.reason='conflict','conflicting_native_reading'
                    else:touched[existing.id]=file.id
                else:
                    row.canonical_key=key;touched[row.id]=file.id
            uow.session.add(row)
            await uow.session.flush()
            uow.session.add(AdaptationResult(evaluation_id=evaluation.id,file_id=file.id,reading_id=row.id,
                position=row.position,scope='record',status='conflict' if row.state=='conflict' else 'invalid' if row.reason else 'parsed',
                reason=row.reason,**self.facts(binding.timezone)))
        return touched

    async def candidates(self,uow,evaluation,binding,touched):
        """Build only intervals touching this publication's canonical observations, including late adjacent pairs."""
        result=[]
        for channel in binding.channels:
            points=(await uow.session.scalars(select(NativeReading).where(NativeReading.binding_id==binding.id,
                NativeReading.binding_revision==binding.revision,NativeReading.source_id==channel.source_id,
                NativeReading.canonical_key.is_not(None)).order_by(NativeReading.instant,NativeReading.id))).all()
            pairs=[]
            for index,point in enumerate(points):
                if channel.semantics=='interval':
                    if point.id not in touched:continue
                    start=point.instant if channel.timestamp_role=='interval_start' else point.instant-timedelta(minutes=channel.sampling_minutes)
                    end=start+timedelta(minutes=channel.sampling_minutes)
                    pairs.append((point,point,start,end,point.value,'candidate'))
                elif index:
                    previous=points[index-1]
                    if previous.id not in touched and point.id not in touched:continue
                    energy,reason=adjacent_delta(previous.instant,previous.value,point.instant,point.value,channel.sampling_minutes)
                    pairs.append((previous,point,previous.instant,point.instant,energy,reason))
                elif point.id in touched:
                    uow.session.add(AdaptationResult(evaluation_id=evaluation.id,file_id=touched[point.id],reading_id=point.id,
                        scope='record',status='reference_only',**self.facts(binding.timezone)))
            for first,last,start,end,energy,reason in pairs:
                file_id=touched.get(last.id) or touched[first.id]
                candidate=None
                if energy is not None:
                    candidate=await uow.session.scalar(select(IntervalCandidate).where(IntervalCandidate.binding_id==binding.id,
                        IntervalCandidate.binding_revision==binding.revision,IntervalCandidate.source_id==channel.source_id,
                        IntervalCandidate.start==start,IntervalCandidate.end==end))
                    if candidate and (candidate.energy!=energy or candidate.first_reading_id!=first.id or candidate.last_reading_id!=last.id):
                        reason='conflict';energy=None
                    elif not candidate:
                        identifier=uuid4()
                        candidate=IntervalCandidate(id=identifier,binding_id=binding.id,binding_revision=binding.revision,
                            source_id=channel.source_id,category_id=channel.category_id,start=start,end=end,energy=energy,unit=channel.unit,
                            first_reading_id=first.id,last_reading_id=last.id,evidence_ref='acquisition:'+identifier.hex,**self.facts(binding.timezone))
                        uow.session.add(candidate);await uow.session.flush()
                uow.session.add(AdaptationResult(evaluation_id=evaluation.id,file_id=file_id,reading_id=last.id,
                    candidate_id=candidate.id if candidate else None,scope='interval',status=reason,reason=None if reason=='candidate' else reason,**self.facts(binding.timezone)))
                if energy is not None:
                    result.append(dict(building_id=str(binding.building_id),source_id=str(channel.source_id),category_id=channel.category_id,
                        start=start.isoformat(),end=end.isoformat(),value=str(energy),unit=channel.unit,
                        source_evidence_ref=candidate.evidence_ref,correlation_ref='acquisition:'+evaluation.correlation_ref.hex))
        return sorted(result,key=lambda r:(r['category_id'],r['start'],r['end'],r['source_id']))

    async def finish(self,evaluation_id,binding,outcome):
        """Record immutable002 result references and own audit together; concurrent recoveries cannot append twice."""
        from ecs_ec.consumption.models import IncorporatedRecord
        async with UnitOfWork(self.database.sessions) as uow:
            await binding_lock(uow,binding.id)
            evaluation=await uow.session.get(PublicationEvaluation,evaluation_id,with_for_update=True)
            if evaluation.state=='completed':return
            if evaluation.input_digest!=digest(evaluation.input_records):raise ValueError('frozen_input_changed')
            evaluation.outcome=outcome.model_dump(mode='json')
            evaluation.state='completed' if outcome.state=='completed' else 'partial_failure'
            if evaluation.state=='completed':evaluation.completed_at=self.clock.now()
            publication=await uow.session.get(NativePublication,evaluation.publication_id)
            publication.state='evaluated' if evaluation.state=='completed' else 'partial_failure'
            deadline=max(evaluation.retain_until,anniversary(self.clock.now(),binding.timezone))
            for result in outcome.results:
                if result.measurement_id:
                    incorporated=await uow.session.get(IncorporatedRecord,result.measurement_id)
                    if incorporated:deadline=max(deadline,incorporated.retain_until)
            evaluation.retain_until=max(evaluation.retain_until,deadline)
            publication.retain_until=max(publication.retain_until,deadline)
            # Protect earlier endpoint files and their sessions/manifests as well as the current resend.
            # Conservative binding-wide extension is intentional; no acquisition purge runs automatically.
            session_ids=select(SftpSessionAttempt.id).where(SftpSessionAttempt.binding_id==binding.id)
            file_ids=select(ReceivedFile.id).where(ReceivedFile.session_id.in_(session_ids))
            for model,condition in [(AcquisitionBinding,AcquisitionBinding.id==binding.id),
                (SftpSessionAttempt,SftpSessionAttempt.binding_id==binding.id),
                (NativePublication,NativePublication.binding_id==binding.id),
                (PublicationEvaluation,PublicationEvaluation.session_id.in_(session_ids)),
                (ReceivedFile,ReceivedFile.session_id.in_(session_ids)),
                (AdaptationResult,AdaptationResult.file_id.in_(file_ids)),
                (NativeReading,NativeReading.binding_id==binding.id),(IntervalCandidate,IntervalCandidate.binding_id==binding.id)]:
                for row in (await uow.session.scalars(select(model).where(condition))).all():row.retain_until=max(row.retain_until,deadline)
            if evaluation.state=='completed':await append_audit(uow,self.clock,binding.timezone,'evaluated',evaluation.id)
            await uow.commit()

    async def recover(self):
        """Resume only nonterminal durable evaluations; confirmed too_early remains a terminal002 result."""
        async with UnitOfWork(self.database.sessions) as uow:
            pending=(await uow.session.execute(select(PublicationEvaluation.publication_id,PublicationEvaluation.id).where(
                PublicationEvaluation.state.in_(('pending','processing','partial_failure'))).order_by(PublicationEvaluation.recorded_at,PublicationEvaluation.id))).all()
        for publication_id,evaluation_id in pending:
            await self.process_sealed(publication_id,evaluation_id)
        return len(pending)
