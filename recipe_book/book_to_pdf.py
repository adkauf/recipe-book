"""Compile a recipe book JSON definition into a single PDF."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import jsonschema
from PIL import Image as PILImage
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Image, NextPageTemplate, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus.tableofcontents import TableOfContents

sys.path.insert(0, str(Path(__file__).parent))
from layouts import LAYOUTS, STANDARD  # noqa: E402
from recipe_to_pdf import load_recipe, register_fonts, validate_recipe  # noqa: E402
from themes import CLASSIC, THEMES  # noqa: E402

ROOT = Path(__file__).parent.parent

_FRONT_MATTER_PAGES = 2  # cover + TOC


# ── Custom document template ────────────────────────────────────────────────

class BookDocTemplate(SimpleDocTemplate):
    """SimpleDocTemplate extended with TOC registration and page numbering."""

    def __init__(self, *args, theme, layout, **kwargs):
        self._theme       = theme
        self._layout      = layout
        self._sbs_templates = []  # populated by configure_book_doc for sidebyside layout
        super().__init__(*args, **kwargs)

    def addPageTemplates(self, pageTemplates):
        super().addPageTemplates(pageTemplates)
        # After SimpleDocTemplate appends its First/Later single-column templates,
        # append the layout's recipe templates so pageTemplates[0] stays First.
        if any(t.id == "Later" for t in pageTemplates):
            for t in self._sbs_templates:
                if not any(pt.id == t.id for pt in self.pageTemplates):
                    super().addPageTemplates([t])

    def handle_pageEnd(self):
        if self.page > _FRONT_MATTER_PAGES:
            page_w = self._layout.page_size[0]
            c = self.canv
            c.saveState()
            c.setFont(self._theme.body_font, 9)
            c.setFillColor(self._theme.light)
            c.drawCentredString(
                page_w / 2,
                0.6 * inch,
                str(self.page - _FRONT_MATTER_PAGES),
            )
            c.restoreState()
        super().handle_pageEnd()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        text       = flowable.getPlainText()
        page       = max(1, self.page - _FRONT_MATTER_PAGES)
        if style_name == "SectionDividerTitle":
            self.notify("TOCEntry", (0, text.title(), page))
        elif style_name == "RecipeTitle":
            self.notify("TOCEntry", (1, text, page))


# ── Validation ─────────────────────────────────────────────────────────────

def validate_book(book, book_path):
    """
    Validate book data against the schema, check recipe file references,
    and validate each referenced recipe against the recipe schema.
    Returns a list of error strings; empty list means valid.
    """
    errors = []

    schema    = json.loads((ROOT / "schema/book.json").read_text())
    book_data = {k: v for k, v in book.items() if k != "$schema"}

    for err in jsonschema.Draft202012Validator(schema).iter_errors(book_data):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"Schema: {path}: {err.message}")

    for section in book_data.get("sections", []):
        for ref in section.get("recipes", []):
            recipe_file = ROOT / "recipes" / f'{ref["file"]}.json'
            if not recipe_file.exists():
                errors.append(f"Missing recipe file: recipes/{ref['file']}.json")
                continue
            recipe = load_recipe(recipe_file)
            errors.extend(validate_recipe(recipe, f'recipes/{ref["file"]}.json'))

    return errors


# ── Extended styles ────────────────────────────────────────────────────────

def make_book_styles(base_styles, theme):
    """Add cover, TOC, and section-divider styles to the base recipe style dict."""
    styles = dict(base_styles)
    b = theme.body_size
    t = theme.title_size
    styles.update({
        "cover_title": ParagraphStyle(
            "CoverTitle",
            fontName=theme.body_font_bold,
            fontSize=t + 8,
            leading=t + 14,
            alignment=TA_CENTER,
            textColor=theme.text,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName=theme.body_font_italic,
            fontSize=t - 12,
            leading=t - 6,
            alignment=TA_CENTER,
            textColor=theme.medium,
        ),
        "cover_description": ParagraphStyle(
            "CoverDescription",
            fontName=theme.body_font,
            fontSize=b + 0.5,
            leading=b + 5.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "cover_byline": ParagraphStyle(
            "CoverByline",
            fontName=theme.body_font,
            fontSize=b + 0.5,
            leading=b + 4.5,
            alignment=TA_CENTER,
            textColor=theme.text,
        ),
        "cover_edition": ParagraphStyle(
            "CoverEdition",
            fontName=theme.body_font_italic,
            fontSize=b - 1.5,
            leading=b + 2.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "toc_heading": ParagraphStyle(
            "TOCHeading",
            fontName=theme.body_font_bold,
            fontSize=t,
            leading=t + 6,
            alignment=TA_LEFT,
            textColor=theme.text,
        ),
        "section_divider_title": ParagraphStyle(
            "SectionDividerTitle",
            fontName=theme.body_font_bold,
            fontSize=t - 6,
            leading=t,
            alignment=TA_CENTER,
            textColor=theme.text,
            charSpace=3,
        ),
        "section_divider_desc": ParagraphStyle(
            "SectionDividerDesc",
            fontName=theme.body_font_italic,
            fontSize=b + 0.5,
            leading=b + 5.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
        "editorial_note": ParagraphStyle(
            "EditorialNote",
            fontName=theme.body_font_italic,
            fontSize=b + 0.5,
            leading=b + 5.5,
            alignment=TA_CENTER,
            textColor=theme.light,
        ),
    })
    return styles


# ── Image helpers ──────────────────────────────────────────────────────────

def _flatten_image(path):
    """Return a temp JPEG path with transparency composited onto white."""
    pil_img = PILImage.open(path).convert("RGBA")
    bg = PILImage.new("RGB", pil_img.size, (255, 255, 255))
    bg.paste(pil_img, mask=pil_img.split()[3])
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    bg.save(tmp.name, format="JPEG", quality=95)
    return tmp.name


# ── Cover page ─────────────────────────────────────────────────────────────

def cover_page(book, styles, theme, layout, cover_image_path=None):
    """Return flowables for the cover page followed by a PageBreak."""
    page_w, page_h = layout.page_size
    margin = theme.margin * inch
    story  = []

    story.append(Spacer(1, (page_h * 0.28) - margin))
    story.append(Paragraph(book["title"], styles["cover_title"]))
    story.append(HRFlowable(width="100%", thickness=2,   color=theme.accent, spaceBefore=10, spaceAfter=3))
    story.append(HRFlowable(width="100%", thickness=0.5, color=theme.accent, spaceBefore=0,  spaceAfter=10))

    if "subtitle" in book:
        story.append(Paragraph(book["subtitle"], styles["cover_subtitle"]))

    if "description" in book and book["description"] != book.get("title"):
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(book["description"], styles["cover_description"]))

    if cover_image_path:
        img   = Image(cover_image_path)
        max_w = page_w - 2 * margin
        max_h = page_h * 0.28
        scale = min(max_w / img.drawWidth, max_h / img.drawHeight)
        img.drawWidth  *= scale
        img.drawHeight *= scale
        img.hAlign = "CENTER"
        story.append(Spacer(1, 0.25 * inch))
        story.append(img)
        story.append(Spacer(1, 0.25 * inch))
    else:
        story.append(Spacer(1, page_h * 0.3))

    byline_parts = []
    if "author" in book:
        byline_parts.append(book["author"])
    if byline_parts:
        story.append(Paragraph("  ·  ".join(byline_parts), styles["cover_byline"]))

    edition_parts = []
    if "edition" in book:
        edition_parts.append(book["edition"])
    if "date" in book:
        edition_parts.append(book["date"][:4])
    if edition_parts:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("  ·  ".join(edition_parts), styles["cover_edition"]))

    story.append(PageBreak())
    return story


# ── Table of contents page ──────────────────────────────────────────────────

def toc_page(styles, theme, layout):
    """Return flowables for the table of contents page followed by a PageBreak."""
    _, page_h = layout.page_size
    b = theme.body_size
    margin = theme.margin * inch

    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [
        ParagraphStyle(
            "TOCSection",
            fontName=theme.body_font_bold,
            fontSize=b,
            leading=b + 7,
            textColor=theme.text,
            spaceAfter=1,
        ),
        ParagraphStyle(
            "TOCRecipe",
            fontName=theme.body_font,
            fontSize=b - 0.5,
            leading=b + 5,
            textColor=theme.text,
            leftIndent=16,
        ),
    ]

    return [
        Spacer(1, (page_h * 0.15) - margin),
        Paragraph("Contents", styles["toc_heading"]),
        HRFlowable(width="100%", thickness=2,   color=theme.accent, spaceBefore=8, spaceAfter=3),
        HRFlowable(width="100%", thickness=0.5, color=theme.accent, spaceBefore=0, spaceAfter=20),
        toc,
        PageBreak(),
    ]


# ── Section divider ────────────────────────────────────────────────────────

def section_divider(section, styles, theme, layout, next_template=None):
    """Return flowables for a section break page followed by a PageBreak."""
    _, page_h = layout.page_size
    margin = theme.margin * inch
    story  = []

    story.append(Spacer(1, (page_h * 0.42) - margin))
    story.append(Paragraph(section["title"].upper(), styles["section_divider_title"]))
    story.append(HRFlowable(width="60%", thickness=0.75, color=theme.accent, spaceBefore=12, spaceAfter=0))

    if "description" in section:
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(section["description"], styles["section_divider_desc"]))

    if next_template:
        story.append(NextPageTemplate(next_template))
    story.append(PageBreak())
    return story


# ── Compiler ────────────────────────────────────────────────────────────────

def compile_book(book_path, output_dir, theme=CLASSIC, layout=STANDARD):
    """Compile a book JSON into a single PDF and return the output path."""
    register_fonts()

    book_path = Path(book_path)
    book      = json.loads(book_path.read_text())

    errors = validate_book(book, book_path)
    if errors:
        for e in errors:
            print(f"  ERROR  {e}", file=sys.stderr)
        sys.exit(1)

    output_dir  = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{book_path.stem}.pdf"

    keywords = [book.get("theme", ""), "cookbook", book.get("author", "")]
    keywords = [k for k in keywords if k]

    page_w, _ = layout.page_size
    margin     = theme.margin * inch
    text_width = page_w - 2 * margin

    doc = BookDocTemplate(
        str(output_path),
        theme=theme,
        layout=layout,
        pagesize=layout.page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=book["title"],
        subject=book.get("theme", ""),
        author=book.get("author", ""),
        keywords=", ".join(keywords),
    )

    recipe_data = [
        (load_recipe(ROOT / "recipes" / f'{ref["file"]}.json')["title"], ref.get("note"))
        for section in book["sections"] for ref in section["recipes"]
    ]
    layout.configure_book_doc(doc, theme, recipe_data=recipe_data)

    base_styles = layout.make_styles(theme)
    styles      = make_book_styles(base_styles, theme)

    tmp_image = None
    if "cover_image" in book:
        image_path = ROOT / book["cover_image"]
        if image_path.exists():
            tmp_image = _flatten_image(image_path)

    story = [NextPageTemplate("Later")]  # ensure cover/TOC use single-column template
    story.extend(cover_page(book, styles, theme, layout, cover_image_path=tmp_image))
    story.extend(toc_page(styles, theme, layout))

    all_recipes = [(s, r) for s in book["sections"] for r in s["recipes"]]
    sections = book["sections"]
    recipe_idx = 0

    for s_idx, section in enumerate(sections):
        if section.get("title"):
            story.extend(section_divider(section, styles, theme, layout,
                                         next_template=layout.recipe_first_template_name(recipe_idx)))

        refs = section["recipes"]
        for r_idx, ref in enumerate(refs):
            recipe_file = ROOT / "recipes" / f'{ref["file"]}.json'
            recipe      = load_recipe(recipe_file)

            note_flowables = []
            if ref.get("note"):
                note_flowables = [
                    Paragraph(f'"{ref["note"]}"', styles["editorial_note"]),
                    Spacer(1, 0.15 * inch),
                ]

            recipe_story = layout.build_story(recipe, styles, text_width, theme)
            story.extend(layout.wrap_book_recipe(recipe_story, note_flowables))

            is_last = (ref is all_recipes[-1][1] and section is all_recipes[-1][0])
            recipe_idx += 1
            if not is_last:
                last_in_section = (r_idx == len(refs) - 1)
                next_section_has_divider = (
                    last_in_section
                    and s_idx + 1 < len(sections)
                    and sections[s_idx + 1].get("title")
                )
                if next_section_has_divider:
                    story.extend(layout.section_divider_break())
                else:
                    story.extend(layout.book_page_break(next_recipe_idx=recipe_idx))

    try:
        doc.multiBuild(story)
    finally:
        if tmp_image:
            Path(tmp_image).unlink(missing_ok=True)
    return output_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Compile a recipe book JSON into a PDF.")
    parser.add_argument("book", help="Path to the book JSON file")
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
        help="Page layout for the PDF (default: standard)",
    )
    args = parser.parse_args()

    default_output = ROOT / "output"
    output_dir     = Path(args.output_dir) if args.output_dir else default_output

    output_path = compile_book(
        args.book,
        output_dir,
        theme=THEMES[args.theme],
        layout=LAYOUTS[args.layout],
    )
    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
