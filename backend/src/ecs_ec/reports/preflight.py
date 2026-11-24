"""005 independent pypdf preflight over actual bytes, effective font sizes and measured text boxes."""

from io import BytesIO
from math import hypot
import re
from pypdf import PdfReader


class ValidationError(ValueError):
    """A generated buffer is not an admissible completeA4 document and must never be published."""


def preflight(content, manifest):
    """Verify one unencryptedA4 page, embedded text>=10pt, manifest agreement and nonoverlapping text geometry."""
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) != 1:
            raise ValueError()
        page = reader.pages[0]
        if (
            page.get("/Rotate", 0) % 360
            or abs(float(page.mediabox.width) * 25.4 / 72 - 210) > 0.1
            or abs(float(page.mediabox.height) * 25.4 / 72 - 297) > 0.1
        ):
            raise ValueError()
        observations = []

        def visit(text, cm, tm, font, size):
            """Read actual text operators and effective transform scale independently of the renderer's manifest."""
            if not text.strip():
                return
            effective = (
                size
                * min(hypot(cm[0], cm[1]), hypot(cm[2], cm[3]))
                * min(hypot(tm[0], tm[1]), hypot(tm[2], tm[3]))
            )
            if effective < 9.999 or not font:
                raise ValueError()
            descriptor = font.get("/FontDescriptor")
            descriptor = descriptor.get_object() if descriptor else None
            if not descriptor or not any(
                k in descriptor for k in ("/FontFile", "/FontFile2", "/FontFile3")
            ):
                raise ValueError()
            # This renderer emits horizontal simple TrueType text. Reject unfamiliar transforms/fonts
            # rather than pretend their dimensions can be checked with this geometry algorithm.
            if (
                any(abs(v) > 1e-8 for v in (cm[1], cm[2], tm[1], tm[2]))
                or cm[0] <= 0
                or cm[3] <= 0
                or tm[0] <= 0
                or tm[3] <= 0
            ):
                raise ValueError()
            cmap = font["/ToUnicode"].get_data().decode("ascii")
            mapping = {}
            for block in re.findall(r"beginbfchar(.*?)endbfchar", cmap, re.S):
                for code, unicode in re.findall(
                    r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block
                ):
                    mapping[bytes.fromhex(unicode).decode("utf-16-be")] = int(code, 16)
            label = text.strip()
            widths = font["/Widths"]
            first = int(font["/FirstChar"])
            width = (
                sum(float(widths[mapping[char] - first]) for char in label)
                * size
                * cm[0]
                * tm[0]
                / 1000
            )
            observations.append(
                (
                    label,
                    tm[4] * cm[0] + tm[5] * cm[2] + cm[4],
                    tm[4] * cm[1] + tm[5] * cm[3] + cm[5],
                    width,
                    effective,
                )
            )

        extracted = page.extract_text(visitor_text=visit)
        boxes = manifest["boxes"]
        if len(observations) != len(boxes):
            raise ValueError()
        required = {
            "identification",
            "energy",
            "chart",
            "costs",
            "comparison",
            "quality",
        }
        if {b["section"] for b in boxes} != required:
            raise ValueError()
        for index, box in enumerate(boxes):
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            if (
                box["font_size"] < 10
                or x < 28.3
                or y < 28.3
                or x + w > 567.1
                or y + h > 813.6
            ):
                raise ValueError()
            matches = [
                o
                for o in observations
                if o[0] == box["text"].strip()
                and abs(o[1] - x) < 0.1
                and abs(o[2] - (y + 3)) < 0.1
                and abs(o[3] - w) < 0.1
                and abs(o[4] - box["font_size"]) < 0.01
            ]
            if len(matches) != 1:
                raise ValueError()
            observations.remove(matches[0])
            for other in boxes[:index]:
                if (
                    min(x + w, other["x"] + other["width"]) - max(x, other["x"]) > 0.1
                    and min(y + h, other["y"] + other["height"]) - max(y, other["y"])
                    > 0.1
                ):
                    raise ValueError()
        for text in (
            "ECS-EC",
            "CAT-01",
            "CAT-07",
            "kWh",
            "Calidad",
            "Contraste",
            "Costos",
        ):
            if text not in extracted:
                raise ValueError()
        return dict(
            page_count=1, page_width_mm=210, page_height_mm=297, minimum_font_pt=10
        )
    except Exception:
        raise ValidationError("validacion_documento_fallida") from None
