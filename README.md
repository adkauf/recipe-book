# Recipe Book

## Overview

A Python tool for generating professional recipe PDFs from JSON source data. Recipes are authored as structured JSON files and compiled into individual PDFs or multi-recipe books with cover pages, tables of contents, and section dividers.

## Project Structure

```
recipe-book/
├── recipes/          # Individual recipe JSON files (private, not tracked)
├── books/            # Recipe book definitions (private, not tracked)
├── schema/           # JSON schemas for recipes and books
├── recipe_book/      # Python source
│   ├── recipe_to_pdf.py   # Generates a single recipe PDF
│   ├── book_to_pdf.py     # Compiles a full recipe book PDF
│   ├── layouts.py         # Page layout strategies
│   ├── themes.py          # Visual themes
│   └── check_glyphs.py    # Verifies font glyph coverage for recipe/book text
├── output/           # Generated PDFs
├── images/           # Cover images (private, not tracked)
├── gen_all.sh        # Batch script to generate everything
└── drive_backup.sh   # Back up / restore private content via Google Drive
```

The `recipes/`, `books/`, and `images/` directories contain private content
and are excluded from version control via `.gitignore`. Use
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
./gen_all.sh
```
`gen_all.sh` defaults to `--theme print --layout sidebyside`. It runs the
glyph coverage check first and exits with a non-zero status if the check or
any generation fails.

**Back up / restore private content (recipes, books, cover images):**
```sh
./drive_backup.sh backup    # mirror recipes/, books/, images/ to Google Drive
./drive_backup.sh restore   # copy them back from Google Drive
```
Requires [rclone](https://rclone.org/) with a configured Google Drive remote
(run `rclone config` once and name the remote `gdrive`). The backup location
defaults to `gdrive:recipe-book-backup`; override it with a second argument
(`./drive_backup.sh backup mydrive:some/path`) or the `RECIPE_BACKUP_REMOTE`
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
- [rclone](https://rclone.org/) — optional, only needed for `drive_backup.sh`

Install Python dependencies with:
```sh
pip install -r requirements.txt
```
