"""Collect every ingredient from one or more library recipes, grouped by name.

Usage:
    python3 .claude/skills/shopping-list/gather.py <source>[:<scale>] [...]

Each source is a recipe stem (e.g. "chicken-adobo"), or a path to a menu
(data/menus/*.json) or book (data/books/*.json), which expands to every
recipe it references. An optional ":<scale>" suffix multiplies quantities
(e.g. "buttermilk-biscuits:2", "chili:0.5", "data/menus/x.json:1.5");
a scale on a menu or book applies to each recipe in it. A recipe reached
through several menus/books has its scales added; naming a recipe stem
explicitly sets its scale outright, overriding any menu or book (so
"data/menus/x.json buttermilk-biscuits:2" doubles just the biscuits).

This is the raw material for a shopping list, not the list itself: it does
no unit conversion or cross-name merging (that needs judgment — see the
skill's SKILL.md). Quantities it can parse ("1½", "2 to 3", "1 1/2") are
shown scaled; anything else is shown as written with the multiplier.
"""

import json
import re
import sys
from fractions import Fraction
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[3]
RECIPES_DIR = ROOT / "data" / "recipes"

_VULGAR = {
    "¼": Fraction(1, 4), "½": Fraction(1, 2), "¾": Fraction(3, 4),
    "⅓": Fraction(1, 3), "⅔": Fraction(2, 3), "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8), "⅝": Fraction(5, 8), "⅞": Fraction(7, 8),
    "⅕": Fraction(1, 5), "⅙": Fraction(1, 6),
}
_TO_VULGAR = {v: k for k, v in _VULGAR.items()}
_NUMBER    = r"(?:\d+(?:\.\d+)?)?\s*[" + "".join(_VULGAR) + r"]?|\d+\s+\d+/\d+|\d+/\d+"
_RANGE     = re.compile(rf"^\s*({_NUMBER})\s*(?:-|–|to)\s*({_NUMBER})\s*$")


def _parse_number(text):
    """Parse '2', '1.5', '1½', '½', '1 1/2', '3/4' to a Fraction, else None."""
    text = text.strip()
    if not text:
        return None
    match = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", text)
    if match:
        return int(match[1]) + Fraction(int(match[2]), int(match[3]))
    match = re.fullmatch(r"(\d+(?:\.\d+)?)?\s*([" + "".join(_VULGAR) + r"])?", text)
    if match and (match[1] or match[2]):
        whole = Fraction(match[1]) if match[1] else 0
        return whole + (_VULGAR[match[2]] if match[2] else 0)
    match = re.fullmatch(r"(\d+)/(\d+)", text)
    if match:
        return Fraction(int(match[1]), int(match[2]))
    return None


def _format_number(value):
    """Format a Fraction with a vulgar fraction where one fits, else decimals."""
    whole, frac = divmod(value, 1)
    if frac == 0:
        return str(int(whole))
    if frac in _TO_VULGAR:
        return f"{int(whole) or ''}{_TO_VULGAR[frac]}"
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def scale_quantity(quantity, scale):
    """Return the quantity string scaled, or None if it can't be parsed."""
    if scale == 1:
        return quantity
    single = _parse_number(quantity)
    if single is not None:
        return _format_number(single * scale)
    match = _RANGE.match(quantity)
    if match:
        low, high = _parse_number(match[1]), _parse_number(match[2])
        if low is not None and high is not None:
            return f"{_format_number(low * scale)} to {_format_number(high * scale)}"
    return None


def _menu_refs(menu):
    """Yield (stem, dish note) for every recipe a menu references."""
    for meal in menu.get("meals", []):
        for course in meal.get("courses", []):
            for dish in course.get("dishes", []):
                if "file" in dish:
                    yield dish["file"], dish.get("note")
                else:
                    print(f"  (menu item without a recipe: {dish['name']!r} — "
                          "decide whether it needs buying)", file=sys.stderr)


def _book_refs(book):
    """Yield (stem, None) for every recipe a book references."""
    for section in book.get("sections", []):
        for ref in section.get("recipes", []):
            yield ref["file"], None


def resolve_sources(args):
    """Turn CLI sources into an ordered {stem: scale} dict and dish notes."""
    scales, explicit, dish_notes = {}, {}, {}
    for arg in args:
        source, _, scale_text = arg.rpartition(":") if ":" in arg else (arg, "", "")
        scale = Fraction(scale_text) if scale_text else Fraction(1)
        path = Path(source)
        if not source.endswith(".json"):
            explicit[source] = scale
            scales.setdefault(source, scale)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        refs = _menu_refs(data) if "meals" in data else _book_refs(data)
        for stem, note in refs:
            scales[stem] = scales.get(stem, 0) + scale
            if note:
                dish_notes[stem] = note
    scales.update(explicit)
    return scales, dish_notes


def _amount_text(amount, scale):
    """Display text for one ingredient amount at the given scale."""
    if "descriptor" in amount:
        return f"[{amount['descriptor']}]"
    unit = amount.get("unit", "")
    scaled = scale_quantity(amount["quantity"], scale)
    if scaled is None:
        return f"{amount['quantity']} {unit} ×{_format_number(scale)} (scale by hand)".strip()
    return f"{scaled} {unit}".strip()


def collect(scales, dish_notes):
    """Print the recipe summary; return (ingredient rows, missing stems)."""
    rows, missing = [], []
    print("RECIPES")
    for stem, scale in scales.items():
        recipe_file = RECIPES_DIR / f"{stem}.json"
        if not recipe_file.exists():
            missing.append(stem)
            continue
        recipe = json.loads(recipe_file.read_text(encoding="utf-8"))
        size = recipe.get("yield") or f"{recipe.get('servings')} servings"
        line = f"  {stem}: {recipe['title']} — {size}, ×{_format_number(scale)}"
        if stem in dish_notes:
            line += f"   [menu note: {dish_notes[stem]}]"
        print(line)
        for component in recipe["components"]:
            where = stem + (f" / {component['title']}" if component.get("title") else "")
            for ing in component.get("ingredients", []):
                extra = "; ".join(x for x in (ing.get("preparation"), ing.get("note")) if x)
                if scale != 1 and re.search(r"\d", extra):
                    extra += "  [note unscaled]"
                rows.append((ing["name"].lower(), _amount_text(ing["amount"], scale),
                             extra, where))
    return rows, missing


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    rows, missing = collect(*resolve_sources(sys.argv[1:]))

    print("\nINGREDIENTS (by name; merge synonyms and convert units by hand)")
    current = None
    for name, amount, extra, where in sorted(rows, key=lambda r: (r[0], r[3])):
        if name != current:
            print(f"\n  {name}")
            current = name
        print(f"      {amount:<28} {where}" + (f"   ({extra})" if extra else ""))

    if missing:
        print(f"\nMISSING recipe files: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
