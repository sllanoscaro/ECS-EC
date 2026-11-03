"""Offline comparison of immutable simulator truth with an authorized single-capture003/001/002 export.

Intentional anomalies are not assumed rejected. A difference can describe legitimate
cleaning; missing/limited capture evidence never produces an empty global success.
"""
from datetime import datetime
from decimal import Decimal,localcontext
import json
from pathlib import Path
from uuid import UUID
from pas600_simulator.transport import frozen_files


def instant(value):
    """Parse an aware exported/reference instant, refusing a host-timezone fallback."""
    result=datetime.fromisoformat(value)
    if result.utcoffset() is None:raise ValueError('naive_evidence_time')
    return result


def kwh(value,unit):
    """Shift Decimal exponents exactly for Wh/kWh/MWh without binary float or context rounding."""
    parsed=Decimal(value)
    if not parsed.is_finite():raise ValueError('invalid_evidence_energy')
    sign,digits,exponent=parsed.as_tuple()
    return Decimal((sign,digits,exponent+{'Wh':-3,'kWh':0,'MWh':3}[unit]))


def compare_run(root,reception):
    """Compare only explicit selected categories/contained periods; return6 for differences or5 for insufficient evidence.

    Candidate endpoints and received file/hash/positions remain in the output links.
    Coverage withdrawn/diagnostic/excluded/unavailable is a limitation, never zero.
    """
    root=Path(root)
    export=json.loads(Path(reception).read_text())
    UUID(export['snapshot_id']);cutoff=instant(export['cutoff_at'])
    if export.get('schema_version')!=1:raise ValueError('unsupported_export')
    selection=export['selection'];UUID(selection['building_id'])
    begin,end=instant(selection['period']['start']),instant(selection['period']['end'])
    categories=selection['category_ids'];view=selection['view']
    if begin>=end or not categories or len(set(categories))!=len(categories) or not set(categories)<={f'CAT-{i:02}' for i in range(1,8)} or view not in ('detail','hour','day','month','year'):
        raise ValueError('invalid_selection')
    scenario=json.loads((root/'control/scenario.safe.json').read_text())
    if selection['period']['timezone']!=scenario['timezone']:raise ValueError('selection_timezone_mismatch')
    manifest=json.loads((root/'control/manifest.json').read_text())
    native=export['publication']['manifest']
    ordered=lambda files:sorted(files,key=lambda f:f['name'])
    matched=[p for p in manifest['publications'] if ordered(p['files'])==ordered(native)]
    if len(matched)!=1:raise ValueError('foreign_publication')
    frozen_files(root,matched[0])
    if any(f['sha256']!=next(n['sha256'] for n in native if n['name']==f['name']) for f in export['files']):raise ValueError('file_evidence_mismatch')
    all_expected=[json.loads(line) for line in (root/'control/expected.jsonl').read_text().splitlines()]
    anomalies=[json.loads(line) for line in (root/'control/anomalies.jsonl').read_text().splitlines()]
    absent={(a['category_id'],i) for a in anomalies if a['kind'] in ('missing','format') for i in a['affected_interval_indices']}
    units={c['category_id']:c['meter']['unit'] for c in scenario['categories'] if c['has_meter']}
    expected={}
    for sample in all_expected:
        start,finish=instant(sample['start']),instant(sample['end'])
        if begin<=start and finish<=end:
            expected[(sample['category_id'],start,finish)]=(kwh(sample['energy'],units[sample['category_id']]),(sample['category_id'],sample['index']) in absent)
    snapshot=export['consumption_snapshot']
    differences=[];limitations=[];links=[];observed={}
    if snapshot['status']=='unavailable':limitations.append('consumption_unavailable')
    elif snapshot['status']!='available' or snapshot.get('reason_code') is not None:raise ValueError('invalid_consumption_snapshot')
    if view=='detail' and snapshot['status']=='available':
        if snapshot.get('aggregate_results'):raise ValueError('wrong_view_evidence')
        if {r['category_id'] for r in snapshot['detail_results']}!=set(categories):raise ValueError('incomplete_selected_categories')
        for detail in snapshot['detail_results']:
            category=detail['category_id']
            if detail.get('withdrawn_record_ids'):limitations.append('detail_withdrawn')
            if detail.get('diagnostics'):limitations.append('calculation_diagnostic')
            if detail.get('crossing_record_ids') or detail.get('crossing_diagnostic_ids'):limitations.append('crossing_intervals_excluded')
            for row in detail['rows']:
                start,finish=instant(row['start']),instant(row['end'])
                if start<begin or finish>end:raise ValueError('out_of_selection_row')
                observed[(category,start,finish)]=Decimal(row['energy_kwh'])
            # Compute a logical total only from the real selected calculation basis; never fabricate a native CAT-01 meter.
            if category=='CAT-01' and 'CAT-01' not in units:
                for key in list(expected):
                    _,start,finish=key
                    if ('CAT-01',start,finish) in expected:continue
                    segments=[s for s in detail['configuration_segments'] if instant(s['start'])<=start and instant(s['end'])>=finish and s['source_mode']=='calculated']
                    if len(segments)!=1:continue
                    base=segments[0]['base_categories']
                    contributions=[expected.get((c,start,finish)) for c in base]
                    if base and all(value is not None for value in contributions):
                        with localcontext() as context:
                            context.prec=100
                            expected[('CAT-01',start,finish)]=(sum((v[0] for v in contributions),Decimal(0)),any(v[1] for v in contributions))
        selected={key:value for key,value in expected.items() if key[0] in categories}
        for (category,start,finish),(value,missing) in selected.items():
            actual=observed.pop((category,start,finish),None)
            if missing:
                if actual is not None:differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='unexpected_available_interval',actual=str(actual)))
            elif actual is None:
                # Pending confirmed reception is unknown, never proof that the producer rejected an interval.
                pending=any(e['state']!='completed' for e in export['evaluations'])
                if pending:limitations.append('reception_not_completed')
                elif not limitations:differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='missing_interval',expected=str(value)))
            elif actual!=value:differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='energy_difference',expected=str(value),actual=str(actual)))
        for (category,start,finish),value in observed.items():
            differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='unexpected_interval',actual=str(value)))
        if not selected:limitations.append('no_expected_intervals_in_selection')
    elif snapshot['status']=='available':
        if snapshot.get('detail_results'):raise ValueError('wrong_view_evidence')
        if {r['category_id'] for r in snapshot['aggregate_results']}!=set(categories):limitations.append('incomplete_selected_categories')
        for result in snapshot['aggregate_results']:
            category=result['category_id']
            if result['excluded_blocks']:limitations.append('blocks_excluded')
            if not result['blocks']:limitations.append('no_aggregate_blocks')
            for block in result['blocks']:
                start,finish=instant(block['start']),instant(block['end'])
                if start<begin or finish>end:raise ValueError('out_of_selection_block')
                entries=[(a,b,value) for (c,a,b),value in expected.items() if c==category and start<=a and b<=finish]
                samples=[value for _,_,value in entries]
                if not samples or block['energy_kwh'] is None:
                    limitations.append('aggregate_evidence_insufficient');continue
                wanted_coverage=sum(((b-a).days*86400_000000+(b-a).seconds*1000000+(b-a).microseconds) for a,b,value in entries if not value[1])
                if int(block['covered_duration_us'])!=wanted_coverage:
                    differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='coverage_difference',expected_duration_us=str(wanted_coverage),actual_duration_us=str(block['covered_duration_us'])))
                if str(block['covered_duration_us'])!=str(block['duration_us']):limitations.append('incomplete_coverage')
                with localcontext() as context:
                    context.prec=100
                    wanted=sum((v[0] for v in samples if not v[1]),Decimal(0))
                if Decimal(block['energy_kwh'])!=wanted:differences.append(dict(category_id=category,start=start.isoformat(),end=finish.isoformat(),kind='aggregate_energy_difference',expected=str(wanted),actual=block['energy_kwh']))
        if not snapshot['aggregate_results']:limitations.append('no_aggregate_evidence')
    readings={r['id']:r for r in export['readings']}
    for candidate in export['candidates']:
        links.append(dict(candidate_id=candidate['id'],source_evidence_ref=candidate['evidence_ref'],
            first=readings.get(candidate['first_reading_id']),last=readings.get(candidate['last_reading_id'])))
        if not links[-1]['first'] or not links[-1]['last']:limitations.append('endpoint_evidence_unavailable')
    if not export['evaluations']:limitations.append('no_reception_evidence')
    status='complete' if not limitations else 'not_evaluable' if snapshot['status']=='unavailable' else 'partial'
    return dict(schema_version=1,snapshot_id=export['snapshot_id'],cutoff_at=cutoff.isoformat(),selection=selection,
        comparison_status=status,differences=differences,limitations=sorted(set(limitations)),links=links)
