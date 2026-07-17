---
name: compose-book
description: Compose a recipe-book JSON from recipes already in the library — select recipes, organize them into sections, write front matter and editorial notes, then validate and render the book PDF. Use when the user wants to create, assemble, or reorganize a recipe book.
---

# Compose a book

Turn a stated intent ("a holiday baking book", "all the Hawaiian recipes")
into `data/books/<kebab-case-slug>.json`, validated and rendered. Unlike
add-recipe, nothing is imported: a book is curated from recipes that
already exist in `data/recipes/`.

## 1. Resolve the selection

Check `ls data/books/` first: if the book already exists, update it
instead of starting over.

The user gives either an explicit recipe list or a criterion. For a
criterion, scan the library's `category` and `keywords` fields to build a
candidate list:

```sh
python3 - <<'EOF'
import json, glob
for f in sorted(glob.glob("data/recipes/*.json")):
    r = json.load(open(f))
    print(f.split("/")[-1][:-5], "|", r.get("category", ""),
          "|", ", ".join(r.get("keywords", [])))
EOF
```

Show the user the proposed selection and get agreement before writing
anything — curation is their call. If they name a recipe that doesn't
exist yet, offer to run **add-recipe** first rather than dropping it.

## 2. Organize into sections

Propose a section structure and confirm it. Group by course or type in
meal order (sauces/condiments → salads/sides → mains → sweets), or by
whatever grouping fits the theme. A short book with no natural groups
uses a single untitled section (renders flat, no dividers).

Recipes are referenced by filename stem. Only write stems you have just
verified exist in `data/recipes/` — a typo fails the whole build.

## 3. Write the JSON

`schema/book.json` is the source of truth. House conventions:

- First key is `"$schema": "../../schema/book.json"`; 4-space indent.
- Front matter: `title`, `subtitle`, `theme`, `author` (match the existing
  books unless told otherwise), `edition` ("First Edition"), `date`
  (today, YYYY-MM-DD), and a real one-or-two-sentence `description` —
  not a copy of the title.
- Section `description` is printed on the divider page; write it as warm,
  evocative prose (see the Sauces and Sweets sections of
  `data/books/island-cooking.json` for the target voice).
- Per-recipe `note` is an editorial aside printed with the recipe:
  provenance, tradition, why it earned its place. Write one only when
  there is something real to say — **never stub optional fields**.
  Placeholders print verbatim in the PDF (older books shipped with
  literal "editorial note" text; don't repeat that).
- `cover_image` is optional; the path is relative to the project root and
  must exist under `data/images/`. Keep covers modest — the PDF embeds
  the file as-is, so downscale big photos first (the existing cover is a
  ~600px-wide, 68 KB variant of a 4.5 MB original):

  ```sh
  python3 -c "from PIL import Image; i = Image.open('data/images/<orig>'); i.thumbnail((600, 600)); i.save('data/images/<orig-stem>-small.jpg')"
  ```

## 4. Validate and render

```sh
python3 .claude/skills/add-recipe/validate.py data/books/<slug>.json
python3 recipe_book/check_glyphs.py
python3 recipe_book/book_to_pdf.py data/books/<slug>.json --theme print --layout sidebyside
```

Fix and re-run until all three pass. Then use the **preview-pdf** skill on
the book PDF and check the book-specific surfaces: cover page (image
placement, title/subtitle), table of contents page numbers, each section
divider (title + description, no orphaned divider at a page bottom), and
editorial notes rendering under their recipe titles.

## 5. Wrap up

`data/books/` is gitignored and private — there is nothing to commit.
Remind the user that `./scripts/drive_backup.sh backup` is the only
safety net for the new file, and offer `./scripts/publish.sh` to copy the
PDF to Google Drive.
