"""005 real embedded-fontReportLab renderer: oneA4 page, vectors and a measured manifest, no remote assets."""

from io import BytesIO
from pathlib import Path
import threading
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from ecs_ec.reports.content import sections
from ecs_ec.reports.energy_table import table_rows
from ecs_ec.reports.layout import TextLayout, CompositionError
from ecs_ec.reports.charts import draw_chart
from ecs_ec.core.timezones import iana_zone

FONT_LOCK = threading.Lock()


def register_font():
    """Load the redistributable bundledUnicodeTTF exactly once across concurrent render threads."""
    with FONT_LOCK:
        if "ECS" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont("ECS", str(Path(__file__).parent / "fonts/DejaVuSans.ttf"))
            )


def render(snapshot, report_id, issued_at):
    """Compose all mandatory sections or fail without emitting a partial downloadable document."""
    register_font()
    output = BytesIO()
    canvas = Canvas(output, pagesize=A4, pageCompression=1)
    canvas.setTitle("ECS-EC · Reporte de consumo")
    canvas.setAuthor("ECS-EC")
    boxes = []
    layout = TextLayout(canvas, boxes)
    y = 799
    y = layout.lines(
        "ECS-EC · Reporte " + snapshot.scale, y, size=14, section="identification"
    )
    y = layout.lines(snapshot.building_name, y, section="identification")
    for line in (
        f"{snapshot.start.astimezone(iana_zone(snapshot.timezone)).isoformat()} a {snapshot.end.astimezone(iana_zone(snapshot.timezone)).isoformat()} (fin excluido)",
        f"Zona: {snapshot.timezone} · Corte: {snapshot.cutoff_at.isoformat()}",
        f"Emisión: {issued_at.isoformat()} · {'Provisional' if snapshot.provisional else 'Período terminado'}",
        f"Referencia: {report_id}",
    ):
        y = layout.lines(line, y, section="identification")
    y -= 6
    y = layout.lines(
        "Consumo · siete categorías · kWh / cobertura", y, size=11, section="energy"
    )
    for name, value, coverage, origin, state in table_rows(snapshot):
        columns = [
            (name, 30, 244),
            (value, 282, 90),
            (coverage, 380, 65),
            (origin, 450, 115),
        ]
        next_y = y
        for text, x, width in columns:
            next_y = min(
                next_y, layout.lines(text, y, x=x, width=width, section="energy")
            )
        y = next_y
        y = layout.lines(state, y, x=30, width=535, section="energy")
    y -= 6
    y = draw_chart(canvas, layout, snapshot, y) - 3
    canvas.setFillColorRGB(0.07, 0.09, 0.08)
    content = sections(snapshot)
    for key, title in [
        ("costs", "Costos · ciclos por fecha de cierre"),
        ("comparison", "Contraste · mismos pares y bases"),
        ("quality", "Calidad y procedencia"),
    ]:
        y = layout.lines(title, y, size=11, section=key)
        for line in content[key]:
            y = layout.lines(line, y, section=key)
        y -= 5
    if y < 28.34:
        raise CompositionError("page_overflow")
    canvas.showPage()
    canvas.save()
    return output.getvalue(), dict(
        version=1,
        boxes=boxes,
        sections=[
            "identification",
            "energy",
            "chart",
            "costs",
            "comparison",
            "quality",
        ],
    )
