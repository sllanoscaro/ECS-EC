"""005 dependency smoke tests with real embedded Unicode fonts and an independent reader."""

from importlib.resources import files
from io import BytesIO

import pytest
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from backend.tests.support.pdf_assertions import read_a4_document


def document(*, size=A4):
    """Build a tooling-only PDF in memory; this fixture is never an application result."""
    font = files('ecs_ec.reports').joinpath('fonts/DejaVuSans.ttf')
    pdfmetrics.registerFont(TTFont('ReportsTooling', str(font)))
    output = BytesIO()
    canvas = Canvas(output, pagesize=size)
    canvas.setFont('ReportsTooling', 10)
    canvas.drawString(30, 800, 'Energía · año · medición · kWh')
    canvas.save()
    return output.getvalue()


def test_unicode_toolchain():
    """Installed Python3.14 libraries preserve Spanish text and embed the shipped TTF."""
    reader = read_a4_document(document(), required_text=('Energía · año · medición · kWh',))
    fonts = reader.pages[0]['/Resources']['/Font']
    assert any('/FontFile2' in font.get_object().get('/FontDescriptor', {}) for font in fonts.values())


def test_reader_rejects_wrong_paper():
    """A parseable non-A4 PDF is not accepted merely because it has one page."""
    with pytest.raises(AssertionError):
        read_a4_document(document(size=(600, 900)))
