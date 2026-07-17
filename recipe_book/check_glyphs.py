"""Check that every character in the recipe and book files has a glyph in
the font that will render it.

Layout code (layouts.pdf_text) sends characters in the Unicode Number Forms
block (U+2150–218F, e.g. ⅓ ⅔ ⅛) to the DejaVuSerif fallback font because
Garamond lacks most of them; everything else renders in the theme's body
fonts. This script mirrors that routing and reports any character with no
glyph, so a new fraction or symbol that would print as a missing-glyph box
is caught before it reaches a PDF.

The header fonts (Arial Narrow) are not checked: they only ever render the
fixed section labels (INGREDIENTS, INSTRUCTIONS, …), never text from the
JSON files.
"""

import glob
import json
import sys
import unicodedata
from pathlib import Path

from reportlab.pdfbase.ttfonts import TTFontFile

from menu_to_pdf import ELEGANT_FONT_FILES, ELEGANT_TITLE_FONT
from recipe_to_pdf import FONT_FILES
from themes import THEMES

ROOT = Path(__file__).parent.parent

_FALLBACK_FONT = "DejaVuSerif"
# Fonts that render JSON text: every theme's body faces.
_BODY_FONTS = sorted({
    face
    for theme in THEMES.values()
    for face in (
        theme.body_font,
        theme.body_font_bold,
        theme.body_font_italic,
        theme.body_font_bold_italic,
    )
})


def _is_fallback_char(ch):
    """True if layouts.pdf_text routes this character to the fallback font."""
    return 0x2150 <= ord(ch) <= 0x218F


def _text_chars(value):
    """Yield every character from all strings nested in a JSON value."""
    if isinstance(value, str):
        yield from value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _text_chars(v)
    elif isinstance(value, list):
        for v in value:
            yield from _text_chars(v)


# The chancery title font renders only menu titles; every other elegant
# face renders general menu text.
_ELEGANT_BODY_FONTS = sorted(set(ELEGANT_FONT_FILES) - {ELEGANT_TITLE_FONT})


def _menu_extra_chars(menu_file):
    """Yield characters a menu renders that come from referenced recipes."""
    with open(menu_file, encoding="utf-8") as fh:
        menu = json.load(fh)
    for meal in menu.get("meals", []):
        for course in meal.get("courses", []):
            for dish in course.get("dishes", []):
                if "file" not in dish:
                    continue
                recipe_file = ROOT / "data" / "recipes" / f'{dish["file"]}.json'
                if recipe_file.exists():
                    with open(recipe_file, encoding="utf-8") as rfh:
                        yield from _text_chars(json.load(rfh).get("title", ""))


def check_glyphs(globs=("data/recipes/*.json", "data/books/*.json", "data/menus/*.json")):
    """Return error strings for characters lacking a glyph in their font.

    Book and menu files are checked too: their titles, descriptions, section
    titles, dish names, and notes all render into the PDF in the same body
    fonts. Menu text (including the titles of recipes a menu references)
    additionally renders in the elegant style's EB Garamond faces, so it is
    checked against those as well.
    """
    coverage = {
        name: TTFontFile(path).charToGlyph
        for name, path in {**FONT_FILES, **ELEGANT_FONT_FILES}.items()
    }

    # char -> first file it was seen in; menus tracked separately because
    # their text renders in the elegant fonts too, and menu titles render
    # in the chancery title font.
    seen       = {}
    menu_seen  = {}
    title_seen = {}
    for pattern in globs:
        target = menu_seen if pattern.startswith("data/menus/") else seen
        for f in sorted(glob.glob(str(ROOT / pattern))):
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            for ch in _text_chars(data):
                target.setdefault(ch, Path(f).name)
            if target is menu_seen:
                for ch in _menu_extra_chars(f):
                    target.setdefault(ch, Path(f).name)
                for ch in _text_chars(data.get("title", "")):
                    title_seen.setdefault(ch, Path(f).name)

    errors = []
    checks = [
        (seen, _BODY_FONTS),
        (menu_seen, _BODY_FONTS + _ELEGANT_BODY_FONTS),
        (title_seen, [ELEGANT_TITLE_FONT]),
    ]
    reported = set()
    for chars, body_fonts in checks:
        for ch, first_file in sorted(chars.items()):
            if _is_fallback_char(ch):
                fonts_needed = [_FALLBACK_FONT]
            else:
                fonts_needed = body_fonts
            missing = [name for name in fonts_needed
                       if ord(ch) not in coverage[name] and (ch, name) not in reported]
            if missing:
                reported.update((ch, name) for name in missing)
                char_name = unicodedata.name(ch, "UNKNOWN")
                errors.append(
                    f"U+{ord(ch):04X} {ch!r} ({char_name}, first seen in {first_file}) "
                    f"has no glyph in: {', '.join(missing)}"
                )
    return errors


def main():
    """Entry point."""
    errors = check_glyphs()
    if errors:
        for e in errors:
            print(f"  ERROR  {e}", file=sys.stderr)
        sys.exit(1)
    print("All recipe and book characters have glyphs in their rendering fonts.")


if __name__ == "__main__":
    main()
