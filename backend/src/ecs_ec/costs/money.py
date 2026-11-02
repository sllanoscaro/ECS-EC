"""Exact bounded Decimal arithmetic and canonical JSON for reproducible financial evidence."""

import hashlib
import json
from decimal import Decimal, InvalidOperation, localcontext


def number(value):
    """Parse finite string/Decimal values without float coercion or unbounded numerical exponents."""
    if not isinstance(value, (str, Decimal)) or isinstance(value, str) and len(value) > 128:
        raise ValueError('decimal_text_required')
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError('invalid_decimal') from None
    if not result.is_finite() or len(result.as_tuple().digits) > 100 or not -40 <= result.as_tuple().exponent <= 60:
        raise ValueError('unsupported_decimal')
    return result


def decimal_text(value):
    """Serialize exact finite decimals as fixed canonical strings, preserving sign but not insignificant zeros."""
    value = number(value)
    if not value:
        return '0'
    result = format(value, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def rounded(value, policy):
    """Round to an explicit quantum multiple at the declared precision/mode; never assume CLP tax rules."""
    with localcontext() as context:
        context.prec = policy.precision
        quantum = number(policy.quantum)
        return (value / quantum).quantize(Decimal(1), rounding=policy.mode) * quantum


def canonical_json(value):
    """Return a deterministic UTF-8 JSON representation of typed JSON-compatible captured evidence."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    """Hash the complete canonical evidence, including versions, reference IDs and policy parameters."""
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()
