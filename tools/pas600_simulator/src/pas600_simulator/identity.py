"""Versioned, domain-separated SHA-256 over canonical JSON, with no wall clock."""
import hashlib
import json
from typing import Any


def digest(domain: str, value: Any) -> str:
    """Hash JSON-compatible input; reject nonfinite JSON and separate domains by NUL."""
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256((domain + '\0' + encoded).encode('utf-8')).hexdigest()


def scenario_hashes(scenario) -> tuple[str, str]:
    """Return logical/full hashes; wire format cannot influence logical samples."""
    full = scenario.model_dump(mode='json')
    full['categories'] = sorted(full['categories'], key=lambda category: category['category_id'])
    logical = {key: value for key, value in full.items() if key != 'format'}
    return digest('pas600-logical-v1', logical), digest('pas600-complete-v1', full)
