"""Match untrusted native identities to trusted revisioned descriptors, never to translated category names."""
import re


def resolve_channel(binding,native,observation,filename):
    """Return an exact compatible channel or a safe cause; publisher data cannot authorize or change001 configuration."""
    is_csv=filename.endswith('.csv')
    publisher=binding.publisher_serial if is_csv else binding.publisher_remote_id
    if native.publisher!=publisher:return None,'publisher_mismatch'
    for channel in binding.channels:
        if observation.channel!=(channel.csv_topic_id if is_csv else channel.json_value_item_id):continue
        if is_csv and (native.device_local_id!=channel.device_local_id or native.device_name!=channel.device_name
            or native.sampling_minutes!=channel.sampling_minutes or observation.unit!=channel.unit
            or not filename.startswith(re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]','~',channel.reduced_id)+'_'+re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]','~',channel.device_name)+'_')):
            return None,'descriptor_mismatch'
        if channel.quantity!='energy':return None,'unsupported_quantity'
        return channel,None
    return None,'unknown_channel'
