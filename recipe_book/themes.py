"""Named PDF themes for the recipe book."""

from dataclasses import dataclass

from reportlab.lib.colors import HexColor


@dataclass(frozen=True)
class Theme:
    name: str
    accent: HexColor
    text: HexColor
    medium: HexColor
    light: HexColor
    body_font: str
    body_font_bold: str
    body_font_italic: str
    body_font_bold_italic: str
    header_font: str
    header_font_bold: str
    title_size: int
    body_size: float
    margin: float


CLASSIC = Theme(
    name="classic",
    accent=HexColor("#8B3A0F"),
    text=HexColor("#1C1C1C"),
    medium=HexColor("#555555"),
    light=HexColor("#7A7A7A"),
    body_font="Garamond",
    body_font_bold="Garamond-Bold",
    body_font_italic="Garamond-Italic",
    body_font_bold_italic="Garamond-BoldItalic",
    header_font="ArialNarrow",
    header_font_bold="ArialNarrow-Bold",
    title_size=28,
    body_size=10.5,
    margin=1.25,
)

MODERN = Theme(
    name="modern",
    accent=HexColor("#2B5EA7"),
    text=HexColor("#1A1A1A"),
    medium=HexColor("#444444"),
    light=HexColor("#888888"),
    body_font="Garamond",
    body_font_bold="Garamond-Bold",
    body_font_italic="Garamond-Italic",
    body_font_bold_italic="Garamond-BoldItalic",
    header_font="ArialNarrow",
    header_font_bold="ArialNarrow-Bold",
    title_size=30,
    body_size=11.0,
    margin=1.0,
)

RUSTIC = Theme(
    name="rustic",
    accent=HexColor("#5C7A3E"),
    text=HexColor("#2A1F0E"),
    medium=HexColor("#6B5A4E"),
    light=HexColor("#8A7A6A"),
    body_font="Garamond",
    body_font_bold="Garamond-Bold",
    body_font_italic="Garamond-Italic",
    body_font_bold_italic="Garamond-BoldItalic",
    header_font="ArialNarrow",
    header_font_bold="ArialNarrow-Bold",
    title_size=28,
    body_size=10.5,
    margin=1.5,
)

PRINT = Theme(
    name="print",
    accent=HexColor("#000000"),
    text=HexColor("#000000"),
    medium=HexColor("#000000"),
    light=HexColor("#000000"),
    body_font="Garamond",
    body_font_bold="Garamond-Bold",
    body_font_italic="Garamond-Italic",
    body_font_bold_italic="Garamond-BoldItalic",
    header_font="ArialNarrow",
    header_font_bold="ArialNarrow-Bold",
    title_size=28,
    body_size=12.0,
    margin=0.75,
)

THEMES = {t.name: t for t in (CLASSIC, MODERN, RUSTIC, PRINT)}
