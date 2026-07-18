# Recipe Book

Generates recipe and recipe-book PDFs from JSON via ReportLab.

## Commands

- `./scripts/gen_all.sh` — generate all recipes and books (runs glyph check first; non-zero exit on any failure)
- `python3 recipe_book/recipe_to_pdf.py data/recipes/<name>.json --theme print --layout sidebyside` — single recipe
- `python3 recipe_book/book_to_pdf.py data/books/<name>.json --theme print --layout sidebyside` — single book
- `python3 recipe_book/menu_to_pdf.py data/menus/<name>.json --theme print --style elegant` — single menu card (`--style classic|elegant`; elegant needs the fonts-ebgaramond-extra package)
- `./scripts/publish.sh` — copy `output/*.pdf` to Google Drive
- `./scripts/drive_backup.sh backup|restore` — back up / restore private content
- `python3 .claude/skills/add-recipe/validate.py <file>` — validate a recipe/book/menu JSON against its schema

## Automation

- A PostToolUse hook (`.claude/hooks/validate-content.sh`) auto-validates
  recipe/book/menu JSON (schema + glyph check) after every Write/Edit.
- Skills: `add-recipe` (recipe intake pipeline), `compose-book` (curate
  library recipes into a book), `preview-pdf` (render PDFs to PNG with
  `pdftoppm` for visual inspection — use it before declaring layout/theme
  work done).
- A systemd user timer (`recipe-backup.timer`, machine-local) runs
  `drive_backup.sh backup` daily; check with
  `systemctl --user list-timers recipe-backup.timer`.

## Private content — IMPORTANT

`data/` (containing `recipes/`, `books/`, `menus/`, and `images/`) is
gitignored and exists ONLY locally. Never delete or `git clean` it;
`./scripts/drive_backup.sh backup` is its only safety net.

## Environment (ChromeOS / Crostini)

- Google Drive mounts at `/mnt/chromeos/GoogleDrive/` but ONLY for folders
  explicitly shared with Linux; the MyDrive root is read-only. Currently
  shared: `MyDrive/Recipes` (published PDFs), `MyDrive/Recipe Book` (backups).
- Fonts live at `/usr/share/fonts/chromeos/monotype/` (Garamond, Arial Narrow).

## Constraints

- Recipe, book, and menu JSON must validate against `schema/recipe.json` /
  `schema/book.json` / `schema/menu.json` — the schemas are the source of
  truth for structure.
- All recipe text must pass `recipe_book/check_glyphs.py`; the fonts lack
  some Unicode glyphs, so check after adding text with diacritics.
- Recipe content: title, then servings and serving size (if appropriate),
  then ingredients (listed in order of use), then preparation method.

## Conventions

- Python: PEP 8, pylint-clean.
- Shell scripts: POSIX `sh`, `set -u`, start with `cd "$(dirname "$0")/.."`
  so they run from any directory; live in `scripts/`.
- Workflow: branch → push → PR to `main`; the user merges PRs on GitHub
  (branches auto-delete on merge). Don't commit directly to `main`.
