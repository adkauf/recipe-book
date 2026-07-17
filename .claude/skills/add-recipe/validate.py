"""Validate a recipe, book, or menu JSON file against its schema.

Usage: python3 .claude/skills/add-recipe/validate.py <file.json> [...]

The schema is chosen by the file's parent directory (recipes/ -> recipe,
books/ -> book, menus/ -> menu). Exits non-zero on the first invalid file.
"""

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = {"recipes": "recipe", "books": "book", "menus": "menu"}


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    for arg in sys.argv[1:]:
        path = Path(arg).resolve()
        kind = SCHEMAS.get(path.parent.name)
        if kind is None:
            print(f"{arg}: not under recipes/, books/, or menus/", file=sys.stderr)
            sys.exit(2)
        with open(ROOT / "schema" / f"{kind}.json", encoding="utf-8") as fh:
            schema = json.load(fh)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as exc:
            where = "/".join(str(p) for p in exc.absolute_path) or "(root)"
            print(f"{arg}: INVALID at {where}: {exc.message}", file=sys.stderr)
            sys.exit(1)
        print(f"{arg}: valid ({kind} schema)")


if __name__ == "__main__":
    main()
