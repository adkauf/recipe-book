"""Page layout strategies for recipe PDFs."""

from abc import ABC, abstractmethod

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, FrameBreak, HRFlowable, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

_FrameBreakType = type(FrameBreak())

_FALLBACK_FONT = "DejaVuSerif"


def _fb(text):
    """Wrap Unicode Number Forms characters (U+2150–U+218F) in a fallback font tag."""
    if not any(0x2150 <= ord(ch) <= 0x218F for ch in text):
        return text
    return "".join(
        f'<font face="{_FALLBACK_FONT}">{ch}</font>' if 0x2150 <= ord(ch) <= 0x218F else ch
        for ch in text
    )


# ── Shared rendering utilities ──────────────────────────────────────────────
# Module-level helpers any layout can call as building blocks.

def section_heading(label, styles, theme):
    """Labelled section break with a thin accent rule."""
    return [
        Spacer(1, 0.3 * inch),
        Paragraph(label.upper(), styles["section_header"]),
        HRFlowable(width="100%", thickness=0.75, color=theme.accent, spaceBefore=4, spaceAfter=0),
        Spacer(1, 0.12 * inch),
    ]


def component_subheading(label, styles):
    """Italic sub-header for a named component within a section."""
    return [
        Spacer(1, 0.15 * inch),
        Paragraph(label, styles["component_header"]),
        Spacer(1, 0.06 * inch),
    ]


def ingredient_table(ingredients, styles, text_width, qty_col=1.4 * inch):
    """Two-column table: right-aligned qty | left-aligned name + note."""
    name_col = text_width - qty_col

    rows = []
    for ing in ingredients:
        qty = ing["amount"]["quantity"] if "amount" in ing else ""
        if "amount" in ing and "unit" in ing["amount"]:
            qty += f' {ing["amount"]["unit"]}'
        name = ing["name"]
        if "preparation" in ing:
            name += f", {ing['preparation']}"

        qty_cell  = Paragraph(_fb(qty),  styles["ingredient_qty"])
        name_cell = Paragraph(_fb(name), styles["ingredient_name"])

        if "note" in ing:
            name_content = [name_cell, Paragraph(_fb(ing["note"]), styles["ingredient_note"])]
        else:
            name_content = name_cell

        rows.append([qty_cell, name_content])

    table = Table(rows, colWidths=[qty_col, name_col], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  8),
    ]))
    return table


def variations_table(variations, styles, text_width):
    """Two-column table: italic accent ingredient | substitute text."""
    ing_col  = 1.4 * inch
    text_col = text_width - ing_col

    rows = [
        [
            Paragraph(_fb(v["ingredient"]), styles["variation_ingredient"]),
            Paragraph(_fb(v["substitute"]), styles["variation_text"]),
        ]
        for v in variations
    ]

    table = Table(rows, colWidths=[ing_col, text_col], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  8),
    ]))
    return table


def instruction_table(instructions, styles, text_width):
    """Two-column table: accent step number | body text.

    Used by single-column layouts where the table renders at a known fixed
    width. Side-by-side uses :func:`instruction_lines` instead so steps can
    re-wrap when they cross from the narrow right column onto a full-page
    overflow frame.
    """
    num_col  = 0.3 * inch
    body_col = text_width - num_col

    rows = [
        [
            Paragraph(str(step["order"]),    styles["step_num"]),
            Paragraph(_fb(step["task"]),     styles["step_body"]),
        ]
        for step in sorted(instructions, key=lambda s: int(s["order"]))
    ]

    table = Table(rows, colWidths=[num_col, body_col], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  6),
    ]))
    return table


def variations_lines(variations, styles, theme):
    """Variations as inline-labeled paragraphs that reflow per frame width.

    Each variation is one Paragraph: italic-accent ingredient name, em-dash
    separator, then the substitute text. Side-by-side uses this so variations
    that overflow the right column reflow to the wider body frame.
    """
    accent = theme.accent.hexval().replace("0x", "#")
    italic = theme.body_font_italic
    items  = []
    for v in variations:
        label = (
            f'<font name="{italic}" color="{accent}">'
            f'{_fb(v["ingredient"])}</font>'
        )
        text  = f'{label} — {_fb(v["substitute"])}'
        items.append(Paragraph(text, styles["variation_line"]))
    return items


def instruction_lines(instructions, styles):
    """Numbered instructions as individual paragraphs.

    Each step is a separate Paragraph with a hanging-indent bullet for the
    step number. Unlike :func:`instruction_table`, these flowables re-wrap to
    whatever frame they are placed in — so steps that overflow from a narrow
    column onto a full-page-width page will reflow to the wider frame.
    """
    return [
        Paragraph(
            _fb(step["task"]),
            styles["step_line"],
            bulletText=f'{step["order"]}.',
        )
        for step in sorted(instructions, key=lambda s: int(s["order"]))
    ]


def notes_list(notes, styles):
    """Bulleted paragraphs for recipe-level notes."""
    return [Paragraph(_fb(f"· {note}"), styles["note_item"]) for note in notes]


# ── Layout base class ───────────────────────────────────────────────────────

class Layout(ABC):
    """
    Abstract base for a page layout strategy.

    Subclasses control page size, the full style dictionary, and how recipe
    content is assembled into a list of Platypus flowables. The shared
    utilities above are available as building blocks but are not required.
    """

    name: str = ""
    page_size: tuple = LETTER

    def make_styles(self, theme) -> dict:
        """
        Return the complete style dict for this layout + theme combination.
        Override to add, replace, or remove styles for a different layout.
        """
        b = theme.body_size
        t = theme.title_size
        return {
            "title": ParagraphStyle(
                "RecipeTitle",
                fontName=theme.body_font_bold,
                fontSize=t,
                leading=t + 6,
                alignment=TA_CENTER,
                textColor=theme.text,
                spaceAfter=8,
            ),
            "meta": ParagraphStyle(
                "RecipeMeta",
                fontName=theme.body_font_italic,
                fontSize=b - 0.5,
                leading=b + 3.5,
                alignment=TA_CENTER,
                textColor=theme.light,
            ),
            "section_header": ParagraphStyle(
                "RecipeSectionHeader",
                fontName=theme.header_font_bold,
                fontSize=b - 2.5,
                leading=b - 0.5,
                alignment=TA_LEFT,
                textColor=theme.text,
                charSpace=2.5,
            ),
            "ingredient_qty": ParagraphStyle(
                "RecipeIngredientQty",
                fontName=theme.body_font,
                fontSize=b,
                leading=b + 4.5,
                alignment=TA_RIGHT,
                textColor=theme.light,
            ),
            "ingredient_name": ParagraphStyle(
                "RecipeIngredientName",
                fontName=theme.body_font,
                fontSize=b,
                leading=b + 4.5,
                alignment=TA_LEFT,
                textColor=theme.text,
            ),
            "ingredient_note": ParagraphStyle(
                "RecipeIngredientNote",
                fontName=theme.body_font_italic,
                fontSize=b - 1.5,
                leading=b + 1.5,
                alignment=TA_LEFT,
                textColor=theme.light,
            ),
            "step_num": ParagraphStyle(
                "RecipeStepNum",
                fontName=theme.body_font_bold,
                fontSize=b + 0.5,
                leading=b + 5.5,
                alignment=TA_CENTER,
                textColor=theme.accent,
            ),
            "step_body": ParagraphStyle(
                "RecipeStepBody",
                fontName=theme.body_font,
                fontSize=b + 0.5,
                leading=b + 5.5,
                alignment=TA_LEFT,
                textColor=theme.text,
            ),
            "component_header": ParagraphStyle(
                "RecipeComponentHeader",
                fontName=theme.body_font_italic,
                fontSize=b + 0.5,
                leading=b + 3.5,
                alignment=TA_LEFT,
                textColor=theme.accent,
            ),
            "variation_ingredient": ParagraphStyle(
                "RecipeVariationIngredient",
                fontName=theme.body_font_italic,
                fontSize=b,
                leading=b + 4.5,
                alignment=TA_RIGHT,
                textColor=theme.accent,
            ),
            "variation_text": ParagraphStyle(
                "RecipeVariationText",
                fontName=theme.body_font,
                fontSize=b,
                leading=b + 4.5,
                alignment=TA_LEFT,
                textColor=theme.text,
            ),
            "note_item": ParagraphStyle(
                "RecipeNoteItem",
                fontName=theme.body_font_italic,
                fontSize=b - 0.5,
                leading=b + 3.5,
                alignment=TA_LEFT,
                textColor=theme.light,
                spaceBefore=3,
            ),
        }

    def make_doc(self, filename, theme, **kwargs):
        """Create and return the document template for this layout."""
        kwargs.pop("recipe_title", None)  # consumed by layouts that need it; ignored here
        margin = theme.margin * inch
        return SimpleDocTemplate(
            filename,
            pagesize=self.page_size,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            **kwargs,
        )

    def configure_book_doc(self, doc, theme, **kwargs):
        """Register any extra page templates this layout needs on a book document."""

    def wrap_book_recipe(self, story, note_flowables=None):
        """Wrap a per-recipe story for the book context.
        note_flowables, if provided, are prepended before the recipe content."""
        if note_flowables:
            return list(note_flowables) + list(story)
        return story

    def first_recipe_template(self):
        """Return the page template name to switch to before each recipe, or None."""
        return None

    def recipe_first_template_name(self, recipe_idx=None):
        """Return the page template name for the first page of a given recipe."""
        return self.first_recipe_template()

    def book_page_break(self, next_recipe_idx=None):
        """Return flowables for a page break between recipes in a book."""
        return [PageBreak()]

    def section_divider_break(self):
        """Return flowables for a page break before a section divider."""
        return [PageBreak()]

    @abstractmethod
    def build_story(self, recipe, styles, text_width, theme) -> list:
        """Assemble and return the full list of Platypus flowables for a recipe."""


# ── Standard layout ─────────────────────────────────────────────────────────

class StandardLayout(Layout):
    """
    Single-column layout on LETTER paper.
    Ingredients and instructions stacked, qty|name two-column table.
    """

    name      = "standard"
    page_size = LETTER

    def build_story(self, recipe, styles, text_width, theme):
        story = []

        story.append(Paragraph(recipe["title"], styles["title"]))
        story.append(HRFlowable(width="100%", thickness=2,   color=theme.accent, spaceBefore=0, spaceAfter=3))
        story.append(HRFlowable(width="100%", thickness=0.5, color=theme.accent, spaceBefore=0, spaceAfter=8))

        meta_parts = []
        if "servings" in recipe:
            meta_parts.append(f"Serves {recipe['servings']}")
        if "serving_size" in recipe:
            meta_parts.append(recipe["serving_size"])
        if "yield" in recipe:
            meta_parts.append(f"Yield: {recipe['yield']}")
        if "method" in recipe:
            meta_parts.append(recipe["method"].title())
        if meta_parts:
            story.append(Paragraph("  ·  ".join(meta_parts), styles["meta"]))

        components  = recipe["components"]
        use_headers = any(c.get("title") for c in components)

        story.extend(section_heading("Ingredients", styles, theme))
        for component in components:
            if use_headers and component.get("title") and component.get("ingredients"):
                story.extend(component_subheading(component["title"], styles))
            if component.get("ingredients"):
                story.append(ingredient_table(component["ingredients"], styles, text_width))
                if use_headers:
                    story.append(Spacer(1, 0.08 * inch))

        story.extend(section_heading("Instructions", styles, theme))
        for i, component in enumerate(components):
            if use_headers and component.get("title") and component.get("instructions"):
                story.extend(component_subheading(component["title"], styles))
            if component.get("instructions"):
                story.append(instruction_table(component["instructions"], styles, text_width))
                if use_headers and i < len(components) - 1:
                    story.append(Spacer(1, 0.15 * inch))

        if recipe.get("variations"):
            story.extend(section_heading("Variations", styles, theme))
            story.append(variations_table(recipe["variations"], styles, text_width))

        if recipe.get("notes"):
            story.extend(section_heading("Notes", styles, theme))
            story.extend(notes_list(recipe["notes"], styles))

        if recipe.get("endnotes"):
            story.extend(section_heading("Endnotes", styles, theme))
            story.extend(notes_list(recipe["endnotes"], styles))

        return story


# ── Side-by-side layout ─────────────────────────────────────────────────────

class SideBySideLayout(Layout):
    """
    Two-column layout on LETTER paper using ReportLab Frames.

    Page 1: full-width title frame at top, then left (ingredients) and right
    (instructions) frames side by side.  Any overflow continues on subsequent
    pages in a single full-page-width frame.
    """

    name      = "sidebyside"
    page_size = LETTER

    _LEFT_FRAC = 0.38
    _COL_GAP   = 0.2 * inch
    _HANG      = 16  # hanging-indent points (~3 chars at body size)

    def make_styles(self, theme):
        styles = super().make_styles(theme)
        b = theme.body_size
        h = self._HANG
        styles["meta"] = ParagraphStyle(
            "RecipeMeta",
            fontName=theme.body_font_italic,
            fontSize=b - 0.5,
            leading=b + 3.5,
            alignment=TA_LEFT,
            textColor=theme.light,
            spaceAfter=6,
        )
        styles["ingredient_line"] = ParagraphStyle(
            "RecipeIngredientLine",
            fontName=theme.body_font,
            fontSize=b,
            leading=b + 4,
            alignment=TA_LEFT,
            textColor=theme.text,
            leftIndent=h,
            firstLineIndent=-h,
            spaceAfter=1,
        )
        styles["ingredient_note_line"] = ParagraphStyle(
            "RecipeIngredientNoteLine",
            fontName=theme.body_font_italic,
            fontSize=b - 1.5,
            leading=b + 1.5,
            alignment=TA_LEFT,
            textColor=theme.light,
            leftIndent=h,
            spaceAfter=3,
        )
        # Numbered instruction line: hanging-indent paragraph that reflows per
        # frame width. The bullet (step number) sits at column 0 in accent
        # color; body text starts at leftIndent and continuation lines align
        # under the body.
        step_indent = 0.3 * inch
        styles["step_line"] = ParagraphStyle(
            "RecipeStepLine",
            fontName=theme.body_font,
            fontSize=b + 0.5,
            leading=b + 5.5,
            alignment=TA_LEFT,
            textColor=theme.text,
            leftIndent=step_indent,
            bulletIndent=0,
            bulletFontName=theme.body_font_bold,
            bulletFontSize=b + 0.5,
            bulletColor=theme.accent,
            spaceAfter=10,
        )
        # Variation line: italic-accent ingredient inline with body text.
        # Single paragraph per variation so it reflows on overflow.
        styles["variation_line"] = ParagraphStyle(
            "RecipeVariationLine",
            fontName=theme.body_font,
            fontSize=b,
            leading=b + 4.5,
            alignment=TA_LEFT,
            textColor=theme.text,
            spaceAfter=6,
        )
        return styles

    def _ingredient_lines(self, ingredients, styles):
        items = []
        for ing in ingredients:
            parts = []
            if "amount" in ing:
                qty = ing["amount"]["quantity"]
                if "unit" in ing["amount"]:
                    qty += f' {ing["amount"]["unit"]}'
                parts.append(qty)
            name = ing["name"]
            if "preparation" in ing:
                name += f', {ing["preparation"]}'
            parts.append(name)
            items.append(Paragraph(_fb(" ".join(parts)), styles["ingredient_line"]))
            if "note" in ing:
                items.append(Paragraph(_fb(ing["note"]), styles["ingredient_note_line"]))
        return items

    def configure_book_doc(self, doc, theme, **kwargs):
        # recipe_data: list of (title_str, note_str_or_None) for all recipes in the book
        recipe_data = kwargs.get("recipe_data", [])
        margin  = theme.margin * inch
        gap     = self._COL_GAP
        page_w, page_h = self.page_size
        text_w  = page_w - 2 * margin
        text_h  = page_h - 2 * margin
        b       = theme.body_size

        title_style = ParagraphStyle(
            "_TitleMeasure",
            fontName=theme.body_font_bold,
            fontSize=theme.title_size,
            leading=theme.title_size + 6,
        )
        note_style = ParagraphStyle(
            "_NoteMeasure",
            fontName=theme.body_font_italic,
            fontSize=b + 0.5,
            leading=b + 5.5,
        )

        left_w  = text_w * self._LEFT_FRAC - gap
        right_x = margin + left_w + gap
        right_w = text_w * (1 - self._LEFT_FRAC)

        # Shared overflow template: single full-page-width column
        body_frame = Frame(
            margin, margin, text_w, text_h,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="body",
        )
        body_tpl = PageTemplate(id="recipe_body", frames=[body_frame], pagesize=self.page_size)

        # Per-recipe first-page templates sized to each recipe's own title+note height
        first_tpls = []
        recipe_template_names = []

        entries = recipe_data if recipe_data else [("", None)]
        for i, (title, note) in enumerate(entries):
            if title:
                _, th = Paragraph(title, title_style).wrap(text_w, 9999 * inch)
                title_h = th + 18  # HRs + small buffer
            else:
                title_h = (theme.title_size + 6) * 2 + 20
            if note:
                _, nh = Paragraph(f'"{note}"', note_style).wrap(text_w, 9999 * inch)
                title_h += nh + 0.15 * inch  # note paragraph + Spacer below it

            body_h = text_h - title_h
            tpl_id = f"recipe_first_{i}" if recipe_data else "recipe_first"

            title_frame = Frame(
                margin, margin + body_h, text_w, title_h,
                leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="title",
            )
            left_frame = Frame(
                margin, margin, left_w, body_h,
                leftPadding=0, rightPadding=0, topPadding=8, bottomPadding=0, id="left",
            )
            right_frame_first = Frame(
                right_x, margin, right_w, body_h,
                leftPadding=0, rightPadding=0, topPadding=8, bottomPadding=0, id="right",
            )
            first_tpls.append(PageTemplate(
                id=tpl_id,
                frames=[title_frame, left_frame, right_frame_first],
                pagesize=self.page_size,
            ))
            recipe_template_names.append(tpl_id)

        self._recipe_template_names = recipe_template_names
        # Store templates on the doc; BookDocTemplate.addPageTemplates will add
        # them after SimpleDocTemplate has registered its First/Later templates,
        # ensuring pageTemplates[0] is the single-column cover template.
        doc._sbs_templates = first_tpls + [body_tpl]

    def wrap_book_recipe(self, story, note_flowables=None):
        if note_flowables:
            # Insert notes BEFORE the first FrameBreak so they render in the
            # full-width title frame, below the title HRs.
            result = []
            inserted = False
            for f in story:
                if not inserted and isinstance(f, _FrameBreakType):
                    result.extend(note_flowables)
                    inserted = True
                result.append(f)
            if not inserted:
                result = list(note_flowables) + list(story)
        else:
            result = list(story)
        result.append(NextPageTemplate("Later"))
        return result

    def recipe_first_template_name(self, recipe_idx=None):
        names = getattr(self, "_recipe_template_names", [])
        if names and recipe_idx is not None and recipe_idx < len(names):
            return names[recipe_idx]
        return names[0] if names else "recipe_first"

    def first_recipe_template(self):
        return self.recipe_first_template_name(0)

    def book_page_break(self, next_recipe_idx=None):
        tpl = self.recipe_first_template_name(next_recipe_idx)
        return [NextPageTemplate(tpl), PageBreak()]

    def make_doc(self, filename, theme, **kwargs):
        recipe_title = kwargs.pop("recipe_title", None)
        margin   = theme.margin * inch
        gap      = self._COL_GAP
        page_w, page_h = self.page_size
        text_w   = page_w - 2 * margin
        text_h   = page_h - 2 * margin

        if recipe_title:
            _style = ParagraphStyle(
                "_TitleMeasure",
                fontName=theme.body_font_bold,
                fontSize=theme.title_size,
                leading=theme.title_size + 6,
            )
            _, para_h = Paragraph(recipe_title, _style).wrap(text_w, 9999 * inch)
            # para_h + spaceAfter (8) + two HR lines (~6) + small buffer (4)
            title_h = para_h + 18
        else:
            title_h = (theme.title_size + 6) + 20  # single-line fallback
        body_h   = text_h - title_h
        # Subtract gap from left_w so right column matches its original table-based width
        left_w   = text_w * self._LEFT_FRAC - gap
        right_x  = margin + left_w + gap
        right_w  = text_w * (1 - self._LEFT_FRAC)

        # First page: title (full width, top) + left col + right col below
        title_frame = Frame(
            margin, margin + body_h, text_w, title_h,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id="title",
        )
        left_frame = Frame(
            margin, margin, left_w, body_h,
            leftPadding=0, rightPadding=0, topPadding=8, bottomPadding=0,
            id="left",
        )
        right_frame_first = Frame(
            right_x, margin, right_w, body_h,
            leftPadding=0, rightPadding=0, topPadding=8, bottomPadding=0,
            id="right",
        )

        # Overflow pages: single full-page-width column
        body_frame = Frame(
            margin, margin, text_w, text_h,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id="body",
        )

        first_tpl = PageTemplate(
            id="recipe_first",
            frames=[title_frame, left_frame, right_frame_first],
            pagesize=self.page_size,
        )
        body_tpl = PageTemplate(
            id="recipe_body",
            frames=[body_frame],
            pagesize=self.page_size,
        )

        doc = BaseDocTemplate(filename, pagesize=self.page_size, **kwargs)
        doc.addPageTemplates([first_tpl, body_tpl])
        return doc

    def build_story(self, recipe, styles, text_width, theme):
        right_w = text_width * (1 - self._LEFT_FRAC)

        story = []

        # Activate the overflow template up front: any page break — whether
        # from ingredients spilling out of the left frame or from instructions
        # exceeding the right frame — should land on a full-page-width body
        # page rather than another two-column first-page template.
        story.append(NextPageTemplate("recipe_body"))

        # ── Title frame (full width) ────────────────────────────────────────
        story.append(Paragraph(recipe["title"], styles["title"]))
        story.append(HRFlowable(width="100%", thickness=2,   color=theme.accent, spaceBefore=0, spaceAfter=3))
        story.append(HRFlowable(width="100%", thickness=0.5, color=theme.accent, spaceBefore=0, spaceAfter=0))
        story.append(FrameBreak())  # → left frame

        # ── Left frame: metadata + ingredients ─────────────────────────────
        components  = recipe["components"]
        use_headers = any(c.get("title") for c in components)

        meta_parts = []
        if "servings" in recipe:
            meta_parts.append(f"Serves {recipe['servings']}")
        if "serving_size" in recipe:
            meta_parts.append(recipe["serving_size"])
        if "yield" in recipe:
            meta_parts.append(f"Yield: {recipe['yield']}")
        if "method" in recipe:
            meta_parts.append(recipe["method"].title())
        if meta_parts:
            story.append(Paragraph("  ·  ".join(meta_parts), styles["meta"]))

        for i, component in enumerate(components):
            if component.get("ingredients"):
                story.extend(self._ingredient_lines(component["ingredients"], styles))
            if i < len(components) - 1:
                story.append(Spacer(1, 0.25 * inch))

        if recipe.get("notes"):
            story.extend(section_heading("Notes", styles, theme))
            story.extend(notes_list(recipe["notes"], styles))

        story.append(FrameBreak())              # → right frame

        # ── Right frame: instructions + variations ──────────────────────────
        # Instructions are individual Paragraphs (not a Table) so they reflow
        # to whatever frame they land in — narrow on the page-1 right column,
        # full page width on overflow pages.
        for i, component in enumerate(components):
            if use_headers and component.get("title"):
                story.extend(component_subheading(component["title"], styles))
            if component.get("instructions"):
                story.extend(instruction_lines(component["instructions"], styles))
            if i < len(components) - 1:
                story.append(Spacer(1, 0.25 * inch))

        if recipe.get("variations"):
            story.extend(section_heading("Variations", styles, theme))
            story.extend(variations_lines(recipe["variations"], styles, theme))

        if recipe.get("endnotes"):
            story.extend(section_heading("Endnotes", styles, theme))
            story.extend(notes_list(recipe["endnotes"], styles))

        return story


# ── Registry ────────────────────────────────────────────────────────────────

STANDARD   = StandardLayout()
SIDEBYSIDE = SideBySideLayout()

LAYOUTS = {layout.name: layout for layout in (STANDARD, SIDEBYSIDE)}
