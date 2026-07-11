"""Generate a menu-card PDF from a menu JSON file."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import jsonschema
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, str(Path(__file__).parent))
from layouts import LAYOUTS, STANDARD, pdf_text  # noqa: E402
from recipe_to_pdf import load_recipe, register_fonts, validate_recipe  # noqa: E402
from themes import CLASSIC, THEMES  # noqa: E402

ROOT = Path(__file__).parent.parent

_MENU_SCHEMA_PATH = ROOT / "schema" / "menu.json"

# ── Elegant style fonts ────────────────────────────────────────────────────
# EB Garamond ships as TrueType in the fonts-ebgaramond-extra Debian package.
# Z003 (URW's Zapf Chancery, AGPL-3 with font exception) renders the menu
# title; fonts/Z003-MediumItalic.ttf is a TrueType conversion of the CFF
# original from fonts-urw-base35, which ReportLab cannot load directly.

_EB_DIR = "/usr/share/fonts/truetype/ebgaramond"

ELEGANT_FONT_FILES = {
    "EBGaramond":        f"{_EB_DIR}/EBGaramond12-Regular.ttf",
    "EBGaramond-Italic": f"{_EB_DIR}/EBGaramond12-Italic.ttf",
    "Z003":              str(ROOT / "fonts" / "Z003-MediumItalic.ttf"),
}

# The chancery face renders only the menu title; body text stays EB Garamond.
ELEGANT_TITLE_FONT = "Z003"

_FLEURON      = "❦"          # ❦ floral heart
_FLEURON_PAIR = "☙ ❧"   # ☙ ❧ mirrored pair


def register_elegant_fonts():
    """Register the EB Garamond faces used by the elegant style."""
    missing = [path for path in ELEGANT_FONT_FILES.values() if not Path(path).exists()]
    if missing:
        raise FileNotFoundError(
            "Font file(s) not found: "
            + ", ".join(missing)
            + " — install the fonts-ebgaramond-extra package."
        )
    for name, path in ELEGANT_FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, path))


# ── Validation ─────────────────────────────────────────────────────────────

def validate_menu(menu, menu_path):
    """
    Validate menu data against the schema, check recipe file references,
    and validate each referenced recipe against the recipe schema.
    Returns a list of error strings; empty list means valid.
    """
    errors = []

    schema    = json.loads(_MENU_SCHEMA_PATH.read_text(encoding="utf-8"))
    menu_data = {k: v for k, v in menu.items() if k != "$schema"}

    for err in jsonschema.Draft202012Validator(schema).iter_errors(menu_data):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        if err.context:
            message = " OR ".join(sorted({sub.message for sub in err.context}))
        else:
            message = err.message
        errors.append(f"{menu_path}: {path}: {message}")

    if "date" in menu_data:
        try:
            date.fromisoformat(menu_data["date"])
        except ValueError:
            errors.append(f"{menu_path}: date: {menu_data['date']!r} is not a valid ISO date")

    for meal in menu_data.get("meals", []):
        for course in meal.get("courses", []):
            for dish in course.get("dishes", []):
                if "file" not in dish:
                    continue
                recipe_file = ROOT / "recipes" / f'{dish["file"]}.json'
                if not recipe_file.exists():
                    errors.append(f"Missing recipe file: recipes/{dish['file']}.json")
                    continue
                recipe = load_recipe(recipe_file)
                errors.extend(validate_recipe(recipe, f'recipes/{dish["file"]}.json'))

    return errors


# ── Styles ─────────────────────────────────────────────────────────────────

def make_menu_styles(theme):
    """Return the style dict for the centered menu-card presentation."""
    b = theme.body_size
    t = theme.title_size
    return {
        "title": ParagraphStyle(
            "MenuTitle",
            fontName=theme.body_font_bold,
            fontSize=t,
            leading=t + 6,
            alignment=TA_CENTER,
            textColor=theme.text,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "MenuSubtitle",
            fontName=theme.body_font_italic,
            fontSize=b + 2,
            leading=b + 8,
            alignment=TA_CENTER,
            textColor=theme.medium,
        ),
        "meta": ParagraphStyle(
            "MenuMeta",
            fontName=theme.body_font_italic,
            fontSize=b - 0.5,
            leading=b + 3.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "description": ParagraphStyle(
            "MenuDescription",
            fontName=theme.body_font,
            fontSize=b + 0.5,
            leading=b + 5.5,
            alignment=TA_CENTER,
            textColor=theme.medium,
        ),
        "meal_title": ParagraphStyle(
            "MenuMealTitle",
            fontName=theme.body_font_bold,
            fontSize=t - 10,
            leading=t - 4,
            alignment=TA_CENTER,
            textColor=theme.text,
            charSpace=3,
        ),
        "meal_time": ParagraphStyle(
            "MenuMealTime",
            fontName=theme.body_font_italic,
            fontSize=b - 0.5,
            leading=b + 3.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "course_header": ParagraphStyle(
            "MenuCourseHeader",
            fontName=theme.header_font_bold,
            fontSize=b - 2,
            leading=b + 1,
            alignment=TA_CENTER,
            textColor=theme.accent,
            charSpace=2.5,
        ),
        "dish": ParagraphStyle(
            "MenuDish",
            fontName=theme.body_font,
            fontSize=b + 1.5,
            leading=b + 7,
            alignment=TA_CENTER,
            textColor=theme.text,
        ),
        "dish_note": ParagraphStyle(
            "MenuDishNote",
            fontName=theme.body_font_italic,
            fontSize=b - 1.5,
            leading=b + 1.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "note_item": ParagraphStyle(
            "MenuNoteItem",
            fontName=theme.body_font_italic,
            fontSize=b - 0.5,
            leading=b + 3.5,
            alignment=TA_CENTER,
            textColor=theme.light,
            spaceBefore=3,
        ),
    }


def make_elegant_styles(theme):
    """Return the style dict for the elegant menu-card presentation.

    Typography is EB Garamond throughout; the theme supplies only colors,
    so the print theme yields a pure black-ink card.
    """
    return {
        "title": ParagraphStyle(
            "MenuTitle",
            fontName=ELEGANT_TITLE_FONT,
            fontSize=42,
            leading=50,
            alignment=TA_CENTER,
            textColor=theme.text,
        ),
        "subtitle": ParagraphStyle(
            "MenuSubtitle",
            fontName="EBGaramond-Italic",
            fontSize=14,
            leading=20,
            alignment=TA_CENTER,
            textColor=theme.medium,
        ),
        "meta": ParagraphStyle(
            "MenuMeta",
            fontName="EBGaramond-Italic",
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "description": ParagraphStyle(
            "MenuDescription",
            fontName="EBGaramond",
            fontSize=11.5,
            leading=17,
            alignment=TA_CENTER,
            textColor=theme.medium,
        ),
        "meal_title": ParagraphStyle(
            "MenuMealTitle",
            fontName="EBGaramond",
            fontSize=16,
            leading=21,
            alignment=TA_CENTER,
            textColor=theme.text,
            charSpace=4,
        ),
        "course_header": ParagraphStyle(
            "MenuCourseHeader",
            fontName="EBGaramond",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=theme.medium,
            charSpace=4,
        ),
        "dish": ParagraphStyle(
            "MenuDish",
            fontName="EBGaramond",
            fontSize=14,
            leading=22,
            alignment=TA_CENTER,
            textColor=theme.text,
        ),
        "dish_note": ParagraphStyle(
            "MenuDishNote",
            fontName="EBGaramond-Italic",
            fontSize=9.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "note_item": ParagraphStyle(
            "MenuNoteItem",
            fontName="EBGaramond-Italic",
            fontSize=10,
            leading=15,
            alignment=TA_CENTER,
            textColor=theme.light,
            spaceBefore=3,
        ),
        "ornament": ParagraphStyle(
            "MenuOrnament",
            fontName="EBGaramond",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=theme.accent,
        ),
    }


def _elegant_frame(canvas, doc, theme):
    """Double hairline border frame drawn on every page."""
    page_w, page_h = doc.pagesize
    inset = 0.45 * inch
    gap   = 5
    canvas.saveState()
    canvas.setStrokeColor(theme.text)
    canvas.setLineWidth(1.0)
    canvas.rect(inset, inset, page_w - 2 * inset, page_h - 2 * inset)
    canvas.setLineWidth(0.4)
    canvas.rect(inset + gap, inset + gap,
                page_w - 2 * (inset + gap), page_h - 2 * (inset + gap))
    canvas.restoreState()


# ── Story assembly ─────────────────────────────────────────────────────────

def _format_date(iso_date):
    """Render an ISO date for the menu card, e.g. 'November 26, 2026'."""
    parsed = date.fromisoformat(iso_date)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


def _menu_meta_parts(menu):
    """Build the meta-line strings for a menu: occasion, date, guests."""
    parts = []
    if "occasion" in menu:
        parts.append(menu["occasion"])
    if "date" in menu:
        parts.append(_format_date(menu["date"]))
    if "guests" in menu:
        parts.append(f"Serves {menu['guests']}")
    return parts


def _dish_title(dish):
    """Display title for a dish: the referenced recipe's title, or its name."""
    if "file" in dish:
        return load_recipe(ROOT / "recipes" / f'{dish["file"]}.json')["title"]
    return dish["name"]


def _course_flowables(course, styles):
    """Return flowables for one course: optional header, then its dishes."""
    story = []
    if course.get("title"):
        story.append(Spacer(1, 0.18 * inch))
        story.append(Paragraph(course["title"].upper(), styles["course_header"]))
        story.append(Spacer(1, 0.06 * inch))
    for dish in course["dishes"]:
        story.append(Paragraph(pdf_text(_dish_title(dish)), styles["dish"]))
        if dish.get("note"):
            story.append(Paragraph(pdf_text(dish["note"]), styles["dish_note"]))
    if course.get("description"):
        story.append(Paragraph(pdf_text(course["description"]), styles["dish_note"]))
    return story


def _meal_flowables(meal, styles, theme):
    """Return flowables for one meal: optional title/time, then its courses."""
    story = []
    if meal.get("title"):
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(pdf_text(meal["title"].upper()), styles["meal_title"]))
        story.append(HRFlowable(width="40%", thickness=0.75, color=theme.accent,
                                spaceBefore=8, spaceAfter=2))
    if meal.get("time"):
        story.append(Paragraph(pdf_text(meal["time"]), styles["meal_time"]))
    if meal.get("description"):
        story.append(Spacer(1, 0.06 * inch))
        story.append(Paragraph(pdf_text(meal["description"]), styles["description"]))
    for course in meal["courses"]:
        story.extend(_course_flowables(course, styles))
    return story


def build_menu_story(menu, styles, theme):
    """Assemble the full list of Platypus flowables for a menu."""
    story = []

    story.append(Paragraph(pdf_text(menu["title"]), styles["title"]))
    story.append(HRFlowable(width="100%", thickness=2,   color=theme.accent,
                            spaceBefore=0, spaceAfter=3))
    story.append(HRFlowable(width="100%", thickness=0.5, color=theme.accent,
                            spaceBefore=0, spaceAfter=8))

    if "subtitle" in menu:
        story.append(Paragraph(pdf_text(menu["subtitle"]), styles["subtitle"]))

    meta_parts = _menu_meta_parts(menu)
    if meta_parts:
        story.append(Paragraph(pdf_text("  ·  ".join(meta_parts)), styles["meta"]))

    if "description" in menu:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(pdf_text(menu["description"]), styles["description"]))

    for meal in menu["meals"]:
        story.extend(_meal_flowables(meal, styles, theme))

    if menu.get("notes"):
        story.append(Spacer(1, 0.35 * inch))
        story.append(HRFlowable(width="25%", thickness=0.5, color=theme.accent,
                                spaceBefore=0, spaceAfter=8))
        for note in menu["notes"]:
            story.append(Paragraph(pdf_text(note), styles["note_item"]))

    return story


def _elegant_course_flowables(course, styles):
    """Return flowables for one course in the elegant style."""
    story = [Spacer(1, 0.22 * inch)]
    if course.get("title"):
        story.append(Paragraph(f'— {pdf_text(course["title"].upper())} —',
                               styles["course_header"]))
        story.append(Spacer(1, 0.06 * inch))
    for dish in course["dishes"]:
        story.append(Paragraph(pdf_text(_dish_title(dish)), styles["dish"]))
        if dish.get("note"):
            story.append(Paragraph(pdf_text(dish["note"]), styles["dish_note"]))
    if course.get("description"):
        story.append(Paragraph(pdf_text(course["description"]), styles["dish_note"]))
    return story


def build_elegant_story(menu, styles):
    """Assemble the flowables for the elegant menu-card presentation."""
    story = []

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(pdf_text(menu["title"]), styles["title"]))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(_FLEURON_PAIR, styles["ornament"]))
    story.append(Spacer(1, 0.08 * inch))

    if "subtitle" in menu:
        story.append(Paragraph(pdf_text(menu["subtitle"]), styles["subtitle"]))

    meta_parts = _menu_meta_parts(menu)
    if meta_parts:
        story.append(Paragraph(pdf_text("  ·  ".join(meta_parts)), styles["meta"]))

    if "description" in menu:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(pdf_text(menu["description"]), styles["description"]))

    for meal in menu["meals"]:
        if meal.get("title"):
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph(pdf_text(meal["title"].upper()), styles["meal_title"]))
        if meal.get("time"):
            story.append(Paragraph(pdf_text(meal["time"]), styles["meta"]))
        if meal.get("description"):
            story.append(Spacer(1, 0.06 * inch))
            story.append(Paragraph(pdf_text(meal["description"]), styles["description"]))
        for course in meal["courses"]:
            story.extend(_elegant_course_flowables(course, styles))

    if menu.get("notes"):
        story.append(Spacer(1, 0.45 * inch))
        story.append(Paragraph(_FLEURON, styles["ornament"]))
        story.append(Spacer(1, 0.08 * inch))
        for note in menu["notes"]:
            story.append(Paragraph(pdf_text(note), styles["note_item"]))

    return story


# ── Generator ──────────────────────────────────────────────────────────────

def menu_to_pdf(menu_path, output_dir, theme=CLASSIC, layout=STANDARD, style="classic"):
    """Convert a menu JSON file to a PDF and return the output path.

    The layout argument supplies only the page size; menus always render as
    a single centered column regardless of the recipe layout chosen. The
    elegant style sets EB Garamond throughout, draws a double hairline
    border frame, and uses its own margins; the theme supplies only colors.
    """
    register_fonts()
    if style == "elegant":
        register_elegant_fonts()

    menu_path = Path(menu_path)
    menu      = json.loads(menu_path.read_text(encoding="utf-8"))

    errors = validate_menu(menu, menu_path)
    if errors:
        raise ValueError("Invalid menu:\n" + "\n".join(f"  {e}" for e in errors))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{menu_path.stem}.pdf"

    if style == "elegant":
        h_margin, v_margin = 1.1 * inch, 0.9 * inch
    else:
        h_margin = v_margin = theme.margin * inch

    keywords = ["menu", menu.get("occasion", "")]
    keywords = [k for k in keywords if k]

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=layout.page_size,
        leftMargin=h_margin,
        rightMargin=h_margin,
        topMargin=v_margin,
        bottomMargin=v_margin,
        title=menu["title"],
        subject=menu.get("occasion", ""),
        keywords=", ".join(keywords),
    )

    if style == "elegant":
        story = build_elegant_story(menu, make_elegant_styles(theme))
        def draw_frame(canvas, doc_):
            _elegant_frame(canvas, doc_, theme)
        doc.build(story, onFirstPage=draw_frame, onLaterPages=draw_frame)
    else:
        styles = make_menu_styles(theme)
        doc.build(build_menu_story(menu, styles, theme))
    return output_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Generate a menu-card PDF from a menu JSON file.")
    parser.add_argument("menu", help="Path to the menu JSON file")
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory (default: output/ relative to project root)",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES),
        default="classic",
        help="Visual theme for the PDF (default: classic)",
    )
    parser.add_argument(
        "--layout",
        choices=list(LAYOUTS),
        default="standard",
        help="Accepted for CLI consistency; menus use only the layout's page size",
    )
    parser.add_argument(
        "--style",
        choices=["classic", "elegant"],
        default="classic",
        help="Menu-card presentation: classic matches the recipe styling; "
             "elegant is an EB Garamond card with a border frame (default: classic)",
    )
    args = parser.parse_args()

    default_output = ROOT / "output"
    output_dir     = Path(args.output_dir) if args.output_dir else default_output

    try:
        output_path = menu_to_pdf(
            args.menu,
            output_dir,
            theme=THEMES[args.theme],
            layout=LAYOUTS[args.layout],
            style=args.style,
        )
        print(f"Written to {output_path}")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
