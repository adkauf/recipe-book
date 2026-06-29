"""Generate a PDF from a single recipe JSON file."""

import argparse
import json
import sys
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


from layouts import LAYOUTS, STANDARD
from themes import CLASSIC, THEMES

# ── Fonts ──────────────────────────────────────────────────────────────────

_FONT_DIR = "/usr/share/fonts/chromeos/monotype"


def register_fonts():
    """Register Garamond and Arial Narrow from system fonts."""
    pdfmetrics.registerFont(TTFont("Garamond",            f"{_FONT_DIR}/garamond.ttf"))
    pdfmetrics.registerFont(TTFont("Garamond-Bold",       f"{_FONT_DIR}/garamond-bold.ttf"))
    pdfmetrics.registerFont(TTFont("Garamond-Italic",     f"{_FONT_DIR}/garamond-italic.ttf"))
    pdfmetrics.registerFont(TTFont("Garamond-BoldItalic", f"{_FONT_DIR}/garamond-bolditalic.ttf"))
    pdfmetrics.registerFontFamily(
        "Garamond",
        normal="Garamond",
        bold="Garamond-Bold",
        italic="Garamond-Italic",
        boldItalic="Garamond-BoldItalic",
    )
    pdfmetrics.registerFont(TTFont("ArialNarrow",      f"{_FONT_DIR}/arialn.ttf"))
    pdfmetrics.registerFont(TTFont("ArialNarrow-Bold", f"{_FONT_DIR}/arialnb.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuSerif", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"))


# ── I/O ─────────────────────────────────────────────────────────────────────

def load_recipe(path):
    """Load and return recipe data from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def recipe_to_pdf(recipe_path, output_dir, theme=CLASSIC, layout=STANDARD):
    """Convert a recipe JSON file to a PDF and return the output path."""
    register_fonts()

    recipe_path = Path(recipe_path)
    recipe      = load_recipe(recipe_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{recipe_path.stem}.pdf"

    page_w, _  = layout.page_size
    margin     = theme.margin * inch
    text_width = page_w - 2 * margin

    keywords = recipe.get("keywords", [])
    if recipe.get("category"):
        keywords = [recipe["category"]] + keywords

    doc = layout.make_doc(
        str(output_path),
        theme,
        recipe_title=recipe["title"],
        title=recipe["title"],
        subject=recipe.get("category", ""),
        keywords=", ".join(keywords),
    )

    styles = layout.make_styles(theme)
    story  = layout.build_story(recipe, styles, text_width, theme)
    doc.build(story)
    return output_path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Generate a PDF from a recipe JSON file.")
    parser.add_argument("recipe", help="Path to the recipe JSON file")
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

    default_output = Path(__file__).parent.parent / "output"
    output_dir     = Path(args.output_dir) if args.output_dir else default_output

    try:
        output_path = recipe_to_pdf(
            args.recipe,
            output_dir,
            theme=THEMES[args.theme],
            layout=LAYOUTS[args.layout],
        )
        print(f"Written to {output_path}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
