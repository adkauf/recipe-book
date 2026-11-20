"""Generate a printable shopping-list PDF from a shopping-list JSON file."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import jsonschema
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, FrameBreak, HRFlowable, KeepTogether,
    NextPageTemplate, PageTemplate, Paragraph, Spacer,
)

sys.path.insert(0, str(Path(__file__).parent))
from layouts import pdf_text  # noqa: E402
from recipe_to_pdf import load_recipe, register_fonts, validate_recipe  # noqa: E402
from themes import CLASSIC, THEMES  # noqa: E402

ROOT = Path(__file__).parent.parent

_SCHEMA_PATH = ROOT / "schema" / "shopping-list.json"
_RECIPES_DIR = ROOT / "data" / "recipes"

_FRACTIONS = {0.25: "¼", 0.5: "½", 0.75: "¾"}


# ── Validation ─────────────────────────────────────────────────────────────

def validate_shopping_list(data, path):
    """
    Validate shopping-list data against the schema, check that every recipe
    reference exists and is itself valid, and that each item's `recipes`
    entries name recipes from the top-level list.
    Returns a list of error strings; empty list means valid.
    """
    errors = []

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    body   = {k: v for k, v in data.items() if k != "$schema"}

    for err in jsonschema.Draft202012Validator(schema).iter_errors(body):
        where = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{path}: {where}: {err.message}")
    if errors:
        return errors

    if "date" in body:
        try:
            date.fromisoformat(body["date"])
        except ValueError:
            errors.append(f"{path}: date: {body['date']!r} is not a valid ISO date")

    stems = [r["file"] for r in body["recipes"]]
    for stem in sorted({s for s in stems if stems.count(s) > 1}):
        errors.append(f"{path}: recipes: {stem!r} is listed more than once")
    for stem in dict.fromkeys(stems):
        recipe_file = _RECIPES_DIR / f"{stem}.json"
        if not recipe_file.exists():
            errors.append(f"Missing recipe file: data/recipes/{stem}.json")
            continue
        errors.extend(validate_recipe(load_recipe(recipe_file), f"data/recipes/{stem}.json"))

    for s_idx, section in enumerate(body["sections"]):
        for i_idx, item in enumerate(section["items"]):
            for stem in item.get("recipes", []):
                if stem not in stems:
                    errors.append(
                        f"{path}: sections -> {s_idx} -> items -> {i_idx} ({item['name']}): "
                        f"recipe {stem!r} is not in the top-level recipes list"
                    )
    return errors


# ── Styles ─────────────────────────────────────────────────────────────────

def make_styles(theme):
    """Return the style dict for the shopping list."""
    b = theme.body_size
    return {
        "title": ParagraphStyle(
            "ListTitle",
            fontName=theme.body_font_bold,
            fontSize=theme.title_size,
            leading=theme.title_size + 6,
            textColor=theme.text,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "ListSubtitle",
            fontName=theme.body_font_italic,
            fontSize=b + 1.5,
            leading=b + 6,
            textColor=theme.medium,
        ),
        "meta": ParagraphStyle(
            "ListMeta",
            fontName=theme.body_font,
            fontSize=b - 0.5,
            leading=b + 3.5,
            textColor=theme.medium,
        ),
        "note": ParagraphStyle(
            "ListNote",
            fontName=theme.body_font_italic,
            fontSize=b - 1,
            leading=b + 2.5,
            textColor=theme.light,
            leftIndent=10,
            bulletIndent=0,
            spaceBefore=2,
        ),
        "section": ParagraphStyle(
            "ListSection",
            fontName=theme.body_font_bold,
            fontSize=b - 0.5,
            leading=b + 2,
            textColor=theme.accent,
            charSpace=1.5,
        ),
        "section_desc": ParagraphStyle(
            "ListSectionDesc",
            fontName=theme.body_font_italic,
            fontSize=b - 1.5,
            leading=b + 1.5,
            textColor=theme.light,
            spaceAfter=2,
        ),
        "item": ParagraphStyle(
            "ListItem",
            fontName=theme.body_font,
            fontSize=b,
            leading=b + 2.5,
            textColor=theme.text,
        ),
    }


# ── Flowables ──────────────────────────────────────────────────────────────

class CheckItem(Flowable):
    """A paragraph with an empty tick box drawn beside its first line.

    The box is drawn rather than set as a glyph (☐) because the body fonts
    have no ballot-box character.
    """

    INDENT      = 14    # points from the box's left edge to the text
    SPACE_AFTER = 3.5   # points below each item

    def __init__(self, para, font_size, color):
        super().__init__()
        self.para        = para
        self.font_size   = font_size
        self.color       = color
        self.para_height = 0

    def wrap(self, availWidth, availHeight):  # pylint: disable=invalid-name
        """Size the item to its wrapped paragraph plus trailing space."""
        _, self.para_height = self.para.wrap(availWidth - self.INDENT, availHeight)
        self.width  = availWidth
        self.height = self.para_height + self.SPACE_AFTER
        return self.width, self.height

    def draw(self):
        """Draw the paragraph, then the box sitting on its first baseline."""
        self.para.drawOn(self.canv, self.INDENT, self.SPACE_AFTER)
        box      = self.font_size * 0.62
        baseline = self.SPACE_AFTER + self.para_height - self.font_size
        self.canv.saveState()
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(0.6)
        self.canv.rect(0, baseline, box, box)
        self.canv.restoreState()


# ── Story assembly ─────────────────────────────────────────────────────────

def _format_date(iso_date):
    """Render an ISO date, e.g. 'Thursday, November 26, 2026'."""
    parsed = date.fromisoformat(iso_date)
    return f"{parsed.strftime('%A, %B')} {parsed.day}, {parsed.year}"


def _format_scale(scale):
    """Render a batch multiplier, e.g. 2 -> '×2', 1.5 -> '×1½', 0.5 -> '×½'."""
    whole = int(scale)
    frac  = _FRACTIONS.get(round(scale - whole, 4))
    if frac:
        return f"×{whole or ''}{frac}"
    return f"×{scale:g}"


def _recipe_numbers(data):
    """Map each referenced recipe stem to its 1-based number in the For list."""
    return {ref["file"]: n for n, ref in enumerate(data["recipes"], start=1)}


def _for_line(data):
    """The 'For:' line: numbered recipe titles, with any batch multipliers.

    Items cite recipes by these numbers, which keeps each line short even
    when long recipe titles are involved.
    """
    parts = []
    for n, ref in enumerate(data["recipes"], start=1):
        title = load_recipe(_RECIPES_DIR / f'{ref["file"]}.json')["title"]
        label = f"<b>{n}</b> {pdf_text(title)}"
        if ref.get("scale", 1) != 1:
            label += f" ({_format_scale(ref['scale'])})"
        parts.append(label)
    return "<b>For:</b>  " + "   ".join(parts)


def _item_flowable(item, numbers, styles, theme):
    """One check-box line: bold quantity, name, recipe refs, then note."""
    text = ""
    if item.get("quantity"):
        text += f"<b>{pdf_text(item['quantity'])}</b> "
    text += pdf_text(item["name"])
    if item.get("recipes"):
        refs = ",".join(str(n) for n in sorted(numbers[s] for s in item["recipes"]))
        text += f'<super><font color="{theme.light.hexval()}"> {refs}</font></super>'
    if item.get("note"):
        text += f' <font color="{theme.medium.hexval()}"><i>({pdf_text(item["note"])})</i></font>'
    return CheckItem(Paragraph(text, styles["item"]), styles["item"].fontSize, theme.text)


def _section_flowables(section, numbers, styles, theme):
    """Header, optional description, and items for one store section.

    The header block is kept together with the first item so a section
    title never strands at the bottom of a column.
    """
    head = [
        Spacer(1, 0.14 * inch),
        Paragraph(pdf_text(section["title"].upper()), styles["section"]),
        HRFlowable(width="100%", thickness=0.6, color=theme.accent,
                   spaceBefore=2, spaceAfter=4),
    ]
    if section.get("description"):
        head.append(Paragraph(pdf_text(section["description"]), styles["section_desc"]))
    items = [_item_flowable(item, numbers, styles, theme) for item in section["items"]]
    return [KeepTogether(head + items[:1])] + items[1:]


def build_header(data, styles, theme):
    """Flowables for the full-width header: title, date, For line, notes."""
    header = [
        Paragraph(pdf_text(data["title"]), styles["title"]),
        HRFlowable(width="100%", thickness=2,   color=theme.accent, spaceBefore=0, spaceAfter=3),
        HRFlowable(width="100%", thickness=0.5, color=theme.accent, spaceBefore=0, spaceAfter=6),
    ]
    if "subtitle" in data:
        header.append(Paragraph(pdf_text(data["subtitle"]), styles["subtitle"]))
    if "date" in data:
        header.append(Paragraph(pdf_text(_format_date(data["date"])), styles["meta"]))
    header.append(Paragraph(_for_line(data), styles["meta"]))
    for note in data.get("notes", []):
        header.append(Paragraph(pdf_text(note), styles["note"], bulletText="•"))
    return header


def build_body(data, styles, theme):
    """Flowables for the two-column body: every store section in order."""
    numbers = _recipe_numbers(data)
    body = []
    for section in data["sections"]:
        body.extend(_section_flowables(section, numbers, styles, theme))
    return body


def _page_templates(header, margin, gutter):
    """First page: a full-width header frame sized to fit, then two columns.
    Later pages: two full-height columns."""
    page_w, page_h = LETTER
    width = page_w - 2 * margin
    header_h = 6 + sum(
        f.wrap(width, page_h)[1] + f.getSpaceBefore() + f.getSpaceAfter() for f in header
    )
    col_w = (width - gutter) / 2

    def frame(x, bottom, w, top, frame_id):
        return Frame(x, bottom, w, top - bottom, id=frame_id,
                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def columns(top, prefix):
        return [frame(margin, margin, col_w, top, f"{prefix}-left"),
                frame(margin + col_w + gutter, margin, col_w, top, f"{prefix}-right")]

    header_top    = page_h - margin
    header_bottom = header_top - header_h
    return [
        PageTemplate(id="first", pagesize=LETTER, frames=[
            frame(margin, header_bottom, width, header_top, "header"),
            *columns(header_bottom, "first"),
        ]),
        PageTemplate(id="later", pagesize=LETTER, frames=columns(header_top, "later")),
    ]


# ── Generator ──────────────────────────────────────────────────────────────

def shopping_list_to_pdf(list_path, output_dir, theme=CLASSIC):
    """Convert a shopping-list JSON file to a PDF and return the output path."""
    register_fonts()

    list_path = Path(list_path)
    data      = json.loads(list_path.read_text(encoding="utf-8"))

    errors = validate_shopping_list(data, list_path)
    if errors:
        raise ValueError("Invalid shopping list:\n" + "\n".join(f"  {e}" for e in errors))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{list_path.stem}.pdf"

    margin = min(theme.margin, 0.75) * inch
    styles = make_styles(theme)
    header = build_header(data, styles, theme)
    doc = BaseDocTemplate(
        str(output_path),
        pagesize=LETTER,
        pageTemplates=_page_templates(header, margin, gutter=0.35 * inch),
        title=f"Shopping List: {data['title']}",
        subject="shopping list",
    )
    doc.build(header + [NextPageTemplate("later"), FrameBreak()]
              + build_body(data, styles, theme))
    return output_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Generate a shopping-list PDF from a shopping-list JSON file.")
    parser.add_argument("shopping_list", help="Path to the shopping-list JSON file")
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory (default: output/shopping-lists/ relative to project root)",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES),
        default="classic",
        help="Visual theme for the PDF (default: classic)",
    )
    args = parser.parse_args()

    default_output = ROOT / "output" / "shopping-lists"
    output_dir     = Path(args.output_dir) if args.output_dir else default_output

    try:
        output_path = shopping_list_to_pdf(args.shopping_list, output_dir,
                                           theme=THEMES[args.theme])
        print(f"Written to {output_path}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
