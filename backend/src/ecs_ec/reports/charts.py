"""005 vector evolution from everyCAT-01 producer block, with gaps and repeated-hour offsets preserved."""

from decimal import Decimal, localcontext
from ecs_ec.reports.formatting import number
from ecs_ec.core.timezones import iana_zone


def draw_chart(canvas, layout, snapshot, y):
    """Draw one vector bar per observed block; empty blocks remain outlined gaps with no interpolation."""
    blocks = snapshot.chart_blocks
    if not blocks:
        return layout.lines(
            "Sin detalle disponible para la evolución.", y, section="chart"
        )
    x = 30
    width = 535
    height = 54
    values = [Decimal(b.energy_kwh) for b in blocks if b.energy_kwh is not None]
    maximum = max(values, default=Decimal(0))
    y = layout.lines(
        f"Evolución CAT-01 · kWh · máximo {number(maximum) if values else 'No disponible'}",
        y,
        section="chart",
    )
    bottom = y - height
    step = width / len(blocks)
    if bottom < 50:
        raise ValueError("chart_overflow")
    for index, block in enumerate(blocks):
        canvas.setStrokeColorRGB(0.65, 0.67, 0.66)
        if block.energy_kwh is None:
            canvas.rect(
                x + index * step, bottom, max(0.5, step - 1), 2, fill=0, stroke=1
            )
        else:
            with localcontext() as context:
                context.prec = 200
                h = (
                    float(Decimal(block.energy_kwh) / maximum) * height
                    if maximum
                    else 0
                )
            canvas.setFillColorRGB(0.12, 0.40, 0.28)
            canvas.rect(
                x + index * step, bottom, max(0.5, step - 1), h, fill=1, stroke=0
            )
    # Label density changes only labels, never drops blocks. Actual offset stays visible for daily repeated hours.
    stride = max(1, (len(blocks) + 5) // 6)
    labels = [
        b.start.astimezone(iana_zone(snapshot.timezone)).strftime("%Y-%m-%d %H:%M")
        for b in blocks
    ]
    repeated = {label for label in labels if labels.count(label) > 1}
    for index in range(0, len(blocks), stride):
        block = blocks[index]
        label = str(block.start.astimezone(iana_zone(snapshot.timezone)))
        label = (
            label[11:16] + label[-6:]
            if snapshot.scale == "diario"
            else label[5:10]
            if snapshot.scale == "mensual"
            else label[:7]
        )
        layout.lines(
            label,
            bottom - 13,
            x=x + index * step,
            width=min(110, width - index * step),
            section="chart",
        )
    if repeated:
        times = [
            b.start.astimezone(iana_zone(snapshot.timezone)).strftime("%H:%M %z")
            for b, label in zip(blocks, labels)
            if label in repeated
        ]
        layout.lines(
            "Horas repetidas: " + " / ".join(times), bottom - 29, section="chart"
        )
        return bottom - 52
    return bottom - 39
