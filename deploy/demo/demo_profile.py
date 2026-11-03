"""Stable synthetic descriptors shared by local provisioning and the external publisher."""
import hashlib
from uuid import NAMESPACE_URL, uuid5

EVIDENCE = 'synthetic:ecs-ec-local-demo-interval-v1'
CHECKSUM = hashlib.sha256(EVIDENCE.encode()).hexdigest()
BINDING_ID = str(uuid5(NAMESPACE_URL, EVIDENCE))


def channels():
    """Return seven stable source UUIDs and explicit native interval descriptors."""
    return [dict(source_id=str(uuid5(NAMESPACE_URL, f'{EVIDENCE}/{i}')),
        category_id=f'CAT-0{i}', device_local_id=str(i), reduced_id=f'{i}_mb',
        device_name=f'iEM3150 CAT0{i}', csv_topic_id=f'SYNTHETIC.{i}.energy',
        json_value_item_id=f'synthetic/{i}/energy', unit='kWh', sampling_minutes=15,
        semantics='interval', timestamp_role='interval_end', provenance='synthetic',
        evidence_ref=EVIDENCE, checksum=CHECKSUM) for i in range(1, 8)]
