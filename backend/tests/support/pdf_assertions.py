"""Independent pypdf checks for005 output; these do not certify visual layout."""

from io import BytesIO
from pypdf import PdfReader


def read_a4_document(content: bytes, *, required_text: tuple[str, ...] = ()) -> PdfReader:
    """Assert one unencrypted portrait A4 page and required text; return parsed bytes.

    Dimensions allow at most0.1mm representation error. Font transforms, collisions
    and clipping require additional geometry checks and visual review in T034/T037.
    Malformed bytes propagate pypdf errors rather than being accepted as no data.
    """
    reader = PdfReader(BytesIO(content), strict=True)
    assert not reader.is_encrypted
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert abs(float(page.mediabox.width) * 25.4 / 72 - 210) <= 0.1
    assert abs(float(page.mediabox.height) * 25.4 / 72 - 297) <= 0.1
    assert page.get('/Rotate', 0) % 360 == 0
    extracted = page.extract_text()
    for text in required_text:
        assert text in extracted
    return reader
