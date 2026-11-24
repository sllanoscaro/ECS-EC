"""005 decimal presentation preserves zero, signs and arbitrarily small positive source values."""

from decimal import Decimal, ROUND_HALF_UP, localcontext


def number(value):
    """Show an exact finite producer decimal without float conversion or apparent-zero rounding."""
    if value is None:
        return "No disponible"
    result = format(Decimal(value), "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def money(value, currency, tax_basis):
    """Keep the producer's exact amount, currency and tax basis together; never convert or prorate."""
    return f"{number(value)} {currency} ({tax_basis})"


def percentage(value):
    """Present coverage/ratios to two decimals without turning a nonzero percentage into apparent zero.

    The exact producer value remains in the capture. Energy and money never use this
    display-only precision policy.
    """
    if value is None:
        return "No aplicable"
    amount = Decimal(value)
    if 0 < abs(amount) < Decimal(".01"):
        return ("−" if amount < 0 else "") + "<0.01 %"
    with localcontext() as context:
        context.prec = max(50, len(amount.as_tuple().digits) + 4)
        return number(amount.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)) + " %"
