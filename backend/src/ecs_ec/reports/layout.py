"""Measured005 text layout: fixed10pt floor, explicit boxes, wrapping and functional overflow errors."""

from reportlab.pdfbase.pdfmetrics import stringWidth


class CompositionError(ValueError):
    """Content cannot fit without hiding essential information or violating the10pt floor."""


def wrap(text, width, font="ECS", size=10):
    """Wrap every character, including unbroken identifiers, without truncation or font reduction."""
    result = []
    line = ""
    for word in str(text).split():
        if line and stringWidth(line + " " + word, font, size) <= width:
            line += " " + word
            continue
        if line:
            result.append(line)
            line = ""
        while word and stringWidth(word, font, size) > width:
            cut = 1
            while cut < len(word) and stringWidth(word[: cut + 1], font, size) <= width:
                cut += 1
            result.append(word[:cut])
            word = word[cut:]
        line = word
    if line or not result:
        result.append(line)
    return result


class TextLayout:
    """Record the actual geometry of each painted text line; never rely on a claimed nominal minimum."""

    def __init__(self, canvas, boxes, *, left=30, right=565):
        """Bind oneA4 canvas and a caller-owned manifest; coordinates arePDF points."""
        self.canvas, self.boxes, self.left, self.right = canvas, boxes, left, right

    def lines(self, text, y, *, x=None, width=None, size=10, section="quality"):
        """Paint wrapped lines and return the next baseline; raise before crossing bottom margin."""
        x = self.left if x is None else x
        width = self.right - x if width is None else width
        for line in wrap(text, width, size=size):
            if y < 30 or x < 28.34 or x + stringWidth(line, "ECS", size) > 567:
                raise CompositionError("page_overflow")
            self.canvas.setFont("ECS", size)
            self.canvas.drawString(x, y, line)
            self.boxes.append(
                dict(
                    text=line,
                    x=x,
                    y=y - 3,
                    width=stringWidth(line, "ECS", size),
                    height=size + 3,
                    font_size=size,
                    section=section,
                )
            )
            y -= size + 3
        return y
