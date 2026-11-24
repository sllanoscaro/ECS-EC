"""005 adverse numeric/name lengths must stay legible, embedded and complete, without truncation."""

from io import BytesIO
from copy import deepcopy
from uuid import UUID
import pytest
from pypdf import PdfReader, PdfWriter
from backend.tests.support.report_snapshot import snapshot
from ecs_ec.reports.renderer import render
from ecs_ec.reports.preflight import preflight, ValidationError


@pytest.mark.parametrize("scale", ["diario", "mensual", "anual"])
@pytest.mark.parametrize("value", ["0", "0.000001", "1000000000000"])
def test_reference_extremes_fit(scale, value):
    """All reference names/values fit oneA4 page at>=10pt and exact positive energy survives reopening."""
    source = snapshot(
        scale=scale,
        value=value,
        building_name="Árbol y energía " * 8,
        category_name="Iluminación, ventilación y distribución eléctrica de áreas comunes del edificio. ",
    )
    content, manifest = render(source, UUID(int=5), source.cutoff_at)
    assert preflight(content, manifest)["minimum_font_pt"] >= 10
    text = PdfReader(BytesIO(content)).pages[0].extract_text()
    assert (
        value in text
        and "CAT-07" in text
        and source.building_name.strip() in text.replace("\n", " ")
    )


@pytest.mark.parametrize(
    "tamper", ["missing_box", "fake_width", "small_transform", "corrupt"]
)
def test_preflight_does_not_trust_manifest_or_nominal_font(tamper):
    """Removing/faking manifest geometry or shrinking actualPDF transforms cannot certify a document."""
    source = snapshot()
    content, manifest = render(source, UUID(int=5), source.cutoff_at)
    manifest = deepcopy(manifest)
    if tamper == "missing_box":
        manifest["boxes"].pop()
    if tamper == "fake_width":
        manifest["boxes"][0]["width"] = 0
    if tamper == "corrupt":
        content = b"%PDF-unfinished"
    if tamper == "small_transform":
        from pypdf import Transformation

        writer = PdfWriter(clone_from=BytesIO(content))
        writer.pages[0].add_transformation(Transformation().scale(0.5))
        output = BytesIO()
        writer.write(output)
        content = output.getvalue()
    with pytest.raises(ValidationError):
        preflight(content, manifest)
