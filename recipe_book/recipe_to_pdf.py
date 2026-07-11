"""Generate a PDF from a single recipe JSON file."""

import argparse
import json
import sys
from pathlib import Path

import jsonschema
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


from layouts import LAYOUTS, STANDARD
from themes import CLASSIC, THEMES

_RECIPE_SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "recipe.json"

# ── Fonts ──────────────────────────────────────────────────────────────────

_FONT_DIR = "/usr/share/fonts/chromeos/monotype"

FONT_FILES = {
    "Garamond":            f"{_FONT_DIR}/garamond.ttf",
    "Garamond-Bold":       f"{_FONT_DIR}/garamond-bold.ttf",
    "Garamond-Italic":     f"{_FONT_DIR}/garamond-italic.ttf",
    "Garamond-BoldItalic": f"{_FONT_DIR}/garamond-bolditalic.ttf",
    "ArialNarrow":         f"{_FONT_DIR}/arialn.ttf",
    "ArialNarrow-Bold":    f"{_FONT_DIR}/arialnb.ttf",
    "DejaVuSerif":         "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
}


def register_fonts():
    """Register Garamond and Arial Narrow from system fonts."""
    missing = [path for path in FONT_FILES.values() if not Path(path).exists()]
    if missing:
        raise FileNotFoundError(
            "Font file(s) not found: "
            + ", ".join(missing)
            + " — see the Dependencies section of the README."
        )
    for name, path in FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily(
        "Garamond",
        normal="Garamond",
        bold="Garamond-Bold",
        italic="Garamond-Italic",
        boldItalic="Garamond-BoldItalic",
    )


# ── I/O ─────────────────────────────────────────────────────────────────────

def load_recipe(path):
    """Load and return recipe data from a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_recipe(recipe, recipe_path):
    """
    Validate recipe data against the recipe schema.
    Returns a list of error strings; empty list means valid.
    """
    schema = json.loads(_RECIPE_SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = []
    for err in jsonschema.Draft202012Validator(schema).iter_errors(recipe):
        path = " -> ".join(str(p) for p in err.absolute_path) or "(root)"
        if err.context:
            # Composite failure (anyOf/oneOf): the top-level message dumps the
            # whole instance; the sub-error messages say what actually failed.
            message = " OR ".join(sorted({sub.message for sub in err.context}))
        else:
            message = err.message
        errors.append(f"{recipe_path}: {path}: {message}")
    return errors


def recipe_to_pdf(recipe_path, output_dir, theme=CLASSIC, layout=STANDARD):
    """Convert a recipe JSON file to a PDF and return the output path."""
    register_fonts()

    recipe_path = Path(recipe_path)
    recipe      = load_recipe(recipe_path)

    errors = validate_recipe(recipe, recipe_path)
    if errors:
        raise ValueError("Invalid recipe:\n" + "\n".join(f"  {e}" for e in errors))

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
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
