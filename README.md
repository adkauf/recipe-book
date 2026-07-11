# Recipe Book

## Overview

A Python tool for generating professional recipe PDFs from JSON source data. Recipes are authored as structured JSON files and compiled into individual PDFs or multi-recipe books with cover pages, tables of contents, and section dividers.

## Project Structure

```
recipe-book/
├── recipes/          # Individual recipe JSON files (private, not tracked)
├── books/            # Recipe book definitions (private, not tracked)
├── menus/            # Menu plans for meals or whole days (private, not tracked)
├── schema/           # JSON schemas for recipes, books, and menus
├── recipe_book/      # Python source
│   ├── recipe_to_pdf.py   # Generates a single recipe PDF
│   ├── book_to_pdf.py     # Compiles a full recipe book PDF
│   ├── menu_to_pdf.py     # Generates a menu-card PDF
│   ├── layouts.py         # Page layout strategies
│   ├── themes.py          # Visual themes
│   └── check_glyphs.py    # Verifies font glyph coverage for recipe/book text
├── output/           # Generated PDFs
├── images/           # Cover images (private, not tracked)
├── fonts/            # Fonts shipped with the project (see Dependencies)
└── scripts/
    ├── gen_all.sh        # Batch script to generate everything
    ├── publish.sh        # Copy generated PDFs to Google Drive (ChromeOS)
    └── drive_backup.sh   # Back up / restore private content via Google Drive
```

The `recipes/`, `books/`, `menus/`, and `images/` directories contain
private content and are excluded from version control via `.gitignore`. Use
`drive_backup.sh` (below) to keep them backed up.

## Usage

**Single recipe:**
```sh
python3 recipe_book/recipe_to_pdf.py recipes/loco-moco.json --theme print --layout sidebyside
```

**Full recipe book:**
```sh
python3 recipe_book/book_to_pdf.py books/island-cooking.json --theme print --layout sidebyside
```

**All recipes and books at once:**
```sh
./scripts/gen_all.sh
```
`gen_all.sh` defaults to `--theme print --layout sidebyside`. It runs the
glyph coverage check first and exits with a non-zero status if the check or
any generation fails.

**Publish generated PDFs to Google Drive (ChromeOS):**
```sh
./scripts/publish.sh
```
Copies everything in `output/` to `MyDrive/Recipes` via the ChromeOS Drive
mount. Requires sharing Google Drive with Linux once (Files app →
right-click "Google Drive" → "Share with Linux"). Override the destination
with the `RECIPE_PUBLISH_DIR` environment variable.

**Menu:** plan a single meal (e.g. Thanksgiving dinner) or a whole day of
meals in `menus/*.json`, validated by `schema/menu.json`. Menus are organized
as meals → courses → dishes; a dish either references a library recipe by
filename stem (`"file"`) or is a plain `"name"` for store-bought and
no-recipe items.
```sh
python3 recipe_book/menu_to_pdf.py menus/thanksgiving-dinner.json --theme print --style elegant
```
Renders a centered menu-card PDF; dishes referencing recipes print the
recipe's title. `--style` picks the presentation: `classic` (default)
matches the recipe styling; `elegant` is an EB Garamond card with a
chancery script title, fleuron ornaments, and a double hairline border
frame. `gen_all.sh` also generates all menus (using the elegant style).

**Back up / restore private content (recipes, books, menus, cover images):**
```sh
./scripts/drive_backup.sh backup    # mirror recipes/, books/, menus/, images/ to Google Drive
./scripts/drive_backup.sh restore   # copy them back from Google Drive
```
Uses the same ChromeOS Drive mount as `publish.sh` (requires the one-time
"Share with Linux" step described above). The backup location defaults to
`MyDrive/Recipe Book`; override it with the `RECIPE_BACKUP_DIR`
environment variable. `backup` mirrors the local state (deletions included);
`restore` only adds or updates local files, never deletes them.

### Options

`--theme` — visual theme for the PDF:
- `classic` — warm rust accent, Garamond body, 1.25" margins
- `modern` — blue accent, wider body size, 1.0" margins
- `rustic` — green accent, generous 1.5" margins
- `print` — all black, optimized for physical printing, 0.75" margins

`--layout` — page layout:
- `standard` — single-column layout; ingredients and instructions stacked
- `sidebyside` — two-column layout; ingredients on the left, instructions on the right; overflow pages use a single full-width column

`-o / --output-dir` — output directory (default: `output/`)

## Recipe JSON Format

Each recipe is a JSON file in `recipes/` validated against `schema/recipe.json`.

```jsonc
{
    "$schema": "../schema/recipe.json",
    "title": "Recipe Title",
    "category": "main",         // sauce, condiment, dessert, fermented vegetables, …
    "method": "braising",       // optional cooking method
    "keywords": ["beef", "hawaiian"],
    "yield": "4 servings",      // yield and/or servings — at least one is required
    "servings": 4,
    "serving_size": "1 cup",    // optional
    "time": {                   // optional; all fields freeform strings
        "prep": "15 minutes",
        "inactive": "4 hours",  // marinating, resting, chilling, fermenting
        "cook": "20 minutes",
        "total": "1 day"        // shown instead of the breakdown if present
    },
    "components": [             // one component for simple recipes; multiple for distinct phases
        {
            "title": "Component Name",   // omit for single-component recipes
            "ingredients": [
                {
                    "name": "ground beef",
                    "amount": { "quantity": "1½", "unit": "pounds" },
                    "preparation": "finely chopped",   // optional
                    "note": "80/20 blend preferred"    // optional
                }
            ],
            "instructions": [
                { "task": "Season the beef generously with salt and pepper." }
            ]
        }
    ],
    "notes": ["Note shown before cooking, alongside ingredients."],
    "endnotes": ["Storage tips, cultural background, or serving suggestions shown after instructions."],
    "variations": [
        { "ingredient": "beef", "substitute": "substitute lamb for a richer flavor" }
    ]
}
```

**Conventions:**
- Instructions are numbered by their position in the array — there is no explicit step number field.
- Ingredients are listed in order of use.
- Ingredient names are not capitalized, except for proper nouns.
- Measurement units are spelled out (e.g., `tablespoon`, not `tbsp`).
- Quantities use Unicode fraction characters (e.g., `½`, `¾`, `⅓`).

**Fraction rendering:** not every font covers every Unicode fraction. Garamond
(the body font in all themes) has the Latin-1 fractions `¼ ½ ¾` but lacks most
of the Number Forms block (`⅓ ⅔ ⅕ ⅙ …`), so the layout code automatically
renders any character in that block (U+2150–218F) in the DejaVu Serif fallback
font, which covers them all. Any vulgar fraction is therefore safe to use in a
recipe. To verify that every character in the recipe files has a glyph in the
font that will render it, run:
```sh
python3 recipe_book/check_glyphs.py
```

## Book JSON Format

Recipe books are defined in `books/` and validated against `schema/book.json`.

```jsonc
{
    "$schema": "../schema/book.json",
    "title": "Easy Cooking",
    "subtitle": "Easy Recipe Book",   // optional
    "description": "…",                           // optional
    "theme": "Easy Cooking",
    "author": "John Smith",
    "edition": "First Edition",
    "date": "2026-05-04",
    "cover_image": "images/cover.jpg",           // optional, relative to project root
    "sections": [
        {
            "title": "Sauces",
            "description": "Section description shown on the divider page.",
            "recipes": [
                {
                    "file": "chimichurri",       // stem of the file in recipes/
                    "note": "Editorial note printed alongside this recipe."
                }
            ]
        }
    ]
}
```

Books generate a cover page, table of contents, section divider pages, and numbered pages. Each recipe in a book can include an optional editorial note that appears below the recipe title.

## Dependencies

- Python 3
- [ReportLab](https://www.reportlab.com/) — PDF generation
- [Pillow](https://python-pillow.org/) — cover image processing
- [jsonschema](https://python-jsonschema.readthedocs.io/) — recipe and book validation
- Garamond and Arial Narrow fonts at `/usr/share/fonts/chromeos/monotype/`
- EB Garamond TrueType fonts (`fonts-ebgaramond-extra` Debian package) —
  only needed for the elegant menu style
- `fonts/Z003-MediumItalic.ttf` — URW Zapf Chancery for elegant menu
  titles, shipped in the repo (AGPL-3 with font exception); a TrueType
  conversion of the CFF original from `fonts-urw-base35`, which ReportLab
  cannot load directly

Install Python dependencies with:
```sh
pip install -r requirements.txt
```
