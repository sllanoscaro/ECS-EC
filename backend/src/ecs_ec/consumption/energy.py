"""Exact decimal domain shared by001 and002; no persistence, rounding or float coercion."""

from decimal import Context, Decimal, FloatOperation, Inexact, InvalidOperation, Rounded, localcontext

QUANTUM = Decimal("0.000000000000001")
INDIVIDUAL_LIMIT = Decimal("1e30")
MAX_INDIVIDUAL = Decimal("999999999999999999999999999999.999999999999999")
MAX_CALCULATED = Decimal("5999999999999999999999999999999.999999999999994")


def exact_context() -> Context:
    """Return private precision50 arithmetic trapping any loss or binary-float mixing."""
    context = Context(prec=50)
    for signal in (Inexact, Rounded, InvalidOperation, FloatOperation): context.traps[signal] = True
    return context


def decimal_value(value: object) -> Decimal:
    """Parse textual/integer/Decimal evidence exactly; reject bool, float and non-finite values."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("invalid_energy")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError("invalid_energy") from None
    if not result.is_finite() or result < 0: raise ValueError("invalid_energy")
    return result


def canonical(value: Decimal) -> Decimal:
    """Remove insignificant zeros by tuple manipulation without using the ambient Decimal context."""
    if not value: return Decimal(0)
    sign, digits, exponent = value.as_tuple()
    end = len(digits)
    while end > 1 and digits[end - 1] == 0: end -= 1
    return Decimal((sign, digits[:end], exponent + len(digits) - end))


def supported_energy(value: Decimal, *, calculated=False) -> Decimal:
    """Check kWh after exact conversion; quantum is a divisibility rule, never quantization."""
    value = canonical(decimal_value(value))
    maximum = MAX_CALCULATED if calculated else MAX_INDIVIDUAL
    if value > maximum or value.as_tuple().exponent < -15:
        raise ValueError("energy_out_of_supported_range")
    return value


def to_kwh(value: object, unit: str) -> Decimal:
    """Apply Wh×.001/kWh×1/MWh×1000 and validate identical kWh boundaries in all units."""
    if unit not in ("Wh", "kWh", "MWh"): raise ValueError("unsupported_unit")
    original = canonical(decimal_value(value))
    # Shift the exponent exactly before arithmetic. This rejects extreme exponents safely
    # and strips arbitrary trailing zeros before the precision50 multiplication.
    sign, digits, exponent = original.as_tuple()
    converted = supported_energy(Decimal((sign, digits, exponent + {"Wh": -3, "kWh": 0, "MWh": 3}[unit])))
    with localcontext(exact_context()):
        assert converted == original * {"Wh": Decimal(".001"), "kWh": Decimal(1), "MWh": Decimal(1000)}[unit]
    return converted
