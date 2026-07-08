"""Check that every character in the recipe files has a glyph in the font
that will render it.

Layout code sends characters in the Unicode Number Forms block (U+2150–218F,
e.g. ⅓ ⅔ ⅛) to the DejaVuSerif fallback font because Garamond lacks most of
them; everything else renders in the theme's body/header fonts. This script
mirrors that routing and reports any character with no glyph, so a new
fraction or symbol that would print as a missing-glyph box is caught before
it reaches a PDF.
"""

import glob
import json
import sys
import unicodedata
from pathlib import Path

from reportlab.pdfbase.ttfonts import TTFontFile

from recipe_to_pdf import FONT_FILES

ROOT = Path(__file__).parent.parent

_FALLBACK_FONT = "DejaVuSerif"
_BODY_FONTS    = [name for name in FONT_FILES if name != _FALLBACK_FONT]


def _is_fallback_char(ch):
    """True if layouts._fb routes this character to the fallback font."""
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


def check_glyphs(recipe_glob="recipes/*.json"):
    """Return error strings for characters lacking a glyph in their font."""
    coverage = {
        name: TTFontFile(path).charToGlyph for name, path in FONT_FILES.items()
    }

    # char -> first file it was seen in
    seen = {}
    for f in sorted(glob.glob(str(ROOT / recipe_glob))):
        with open(f, encoding="utf-8") as fh:
            recipe = json.load(fh)
        for ch in _text_chars(recipe):
            seen.setdefault(ch, Path(f).name)

    errors = []
    for ch, first_file in sorted(seen.items()):
        if _is_fallback_char(ch):
            fonts_needed = [_FALLBACK_FONT]
        else:
            fonts_needed = _BODY_FONTS
        missing = [name for name in fonts_needed if ord(ch) not in coverage[name]]
        if missing:
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
    print("All recipe characters have glyphs in their rendering fonts.")


if __name__ == "__main__":
    main()
