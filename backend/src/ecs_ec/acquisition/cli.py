"""Host-only acquisition maintenance CLI; deployment authority is unrelated to human or Programador credentials."""
import argparse,asyncio,json,os,tempfile
from pathlib import Path
from ecs_ec.acquisition.config import AcquisitionSettings,install_binding
from ecs_ec.acquisition.service import Acquisition
from ecs_ec.acquisition.evidence import export_results
from ecs_ec.core.settings import Settings
from ecs_ec.core.database import Database
from ecs_ec.core.clock import SystemClock
from ecs_ec.consumption.queries import Consumption
from ecs_ec.consumption.store import MeasurementStore
from ecs_ec.consumption.reception import Reception


class SafeParser(argparse.ArgumentParser):
    """Reject malformed technical arguments without echoing accidental secrets or private paths."""
    def error(self,message):
        """Return the fixed argument-error exit2; help remains available for the closed command surface."""
        self.exit(2,'Invalid arguments. Use --help for supported options.\n')


def atomic_export(path,payload):
    """Replace output only after a complete capture and fsynced JSON, preserving any prior valid evidence on failure."""
    descriptor,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
            json.dump(payload,stream,sort_keys=True,ensure_ascii=False,allow_nan=False);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)


async def execute(args):
    """Use the shared installed database and caller-owned providers; never create sources or functional users."""
    options=Settings();settings=AcquisitionSettings();clock=SystemClock()
    process=os.environ.get('PAS600_MAINTENANCE_PROCESS','')
    settings.authorize(process)
    database=Database(options.database_url.get_secret_value())
    try:
        if args.command=='install-binding':
            result=await install_binding(database,clock,settings,process,json.loads(args.file.read_text()))
            return {'schema_version':1,'binding_id':str(result.id),'revision':result.revision}
        from sqlalchemy import select
        from ecs_ec.acquisition.models import AcquisitionBinding,NativePublication
        from ecs_ec.core.unit_of_work import UnitOfWork
        async with UnitOfWork(database.sessions) as uow:
            row=await uow.session.scalar(select(NativePublication).where(NativePublication.publication_ref==args.publication_ref))
            if row is None:raise ValueError('publication_not_found')
            binding=await uow.session.get(AcquisitionBinding,(row.binding_id,row.binding_revision))
            building_id=binding.building_id
        consumption=Consumption(database,clock,building_id,MeasurementStore())
        service=Acquisition(database,clock,settings,Reception(database,clock,authorized_processes={}),consumption)
        result=await export_results(service,process=process,publication_ref=args.publication_ref,start=args.start,end=args.end,
            timezone=args.timezone,categories=args.categories.split(','),view=args.view)
        atomic_export(args.output,result)
        return {'schema_version':1,'status':'exported','snapshot_id':result['snapshot_id']}
    finally:await database.close()


def main():
    """Parse only technical maintenance operations; safe failures never print paths, secrets or SQL diagnostics."""
    parser=SafeParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    install=commands.add_parser('install-binding');install.add_argument('--file',type=Path,required=True)
    export=commands.add_parser('export-results')
    for name in ('publication-ref','start','end','timezone','categories'):export.add_argument('--'+name,required=True)
    export.add_argument('--view',choices=('detail','hour','day','month','year'),required=True)
    export.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:print(json.dumps(asyncio.run(execute(args))));return 0
    except PermissionError:
        print('Maintenance process is not authorized.',file=__import__('sys').stderr);return 3
    except Exception:
        print('Acquisition evidence or configuration unavailable.',file=__import__('sys').stderr);return 5


if __name__=='__main__':raise SystemExit(main())
