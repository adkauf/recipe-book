---
name: add-recipe
description: Turn a recipe from any source (URL, pasted text, photo, or scan) into a recipe JSON file that validates, passes the glyph check, and renders to a PDF. Use whenever the user wants to add, import, or transcribe a recipe.
---

# Add a recipe

Convert a source recipe into `data/recipes/<kebab-case-slug>.json`, validate it,
and generate its PDF. The slug comes from the title (e.g. "Chicken Katsu
Curry" → `chicken-katsu-curry`).

## 1. Get the source

- URL → WebFetch the page and extract the recipe.
- Photo or scan → Read the image file.
- Pasted text → use as-is.

Check `ls data/recipes/` first: if the recipe already exists, update that file
instead of creating a duplicate.

## 2. Write the JSON

`schema/recipe.json` is the source of truth for structure. House
conventions on top of it:

- First key is `"$schema": "../../schema/recipe.json"`; 4-space indent.
- Order of content: title, then servings and serving size (or `yield` for
  sauces/condiments — one of `servings`/`yield` is required), then
  ingredients, then instructions.
- `category` and `method` are **closed enums** — see `schema/recipe.json`
  for the allowed values. Pick the closest existing value rather than
  inventing one; the collection is only sortable if these stay controlled.
  `method` is an array, so a recipe that sears then braises gets both.
- Set `cuisine` when the recipe belongs to a regional tradition (Hawaiian,
  Korean, Mexican …). It's freeform, but keep it a bare capitalized
  adjective. Don't also repeat it in `keywords` — `keywords` is for
  everything that isn't already a structured field.
- Record attribution in `source`, never as prose in `endnotes`: any of
  `{name, author, url, page, date, adapted}`. Set `adapted: true` when
  your version departs from the original. The renderer generates the
  credit line ("Adapted from The Border Cookbook, p. 228."), so don't
  write one by hand.
- Add a few `keywords` and `time` when the source gives them.
  `time.total` replaces the prep/inactive/cook breakdown when present,
  so use one or the other.
- Quantities use Unicode vulgar fractions: ¼ ½ ¾ ⅓ ⅔ ⅛ — never "1/4".
  These specific fractions are known-safe; any other exotic character must
  pass the glyph check below.
- List ingredients **in order of use**. Split amount into
  `{"quantity": "...", "unit": "..."}`; put "finely chopped" etc. in
  `preparation`, not in the name.
- **Every ingredient requires `amount`** — the schema enforces this. For
  something with no fixed quantity (a seasoning added to taste, a
  garnish, an item for serving), use `{"descriptor": "..."}` instead of
  `quantity`/`unit` — e.g. `"to taste"`, `"for serving"`, `"as needed"`,
  `"for garnish"`. Reach for a real quantity first if the source gives
  one or a reasonable one is inferable; use `descriptor` only when the
  amount is genuinely open-ended. Don't reach for `"to taste"` on
  ingredients where amount actually matters (e.g. salt in a fermentation
  brine) — give those a real measured quantity instead.
- Use a single untitled component unless the recipe has genuinely distinct
  phases (e.g. sauce + main); then give each component a `title`.
- **Rewrite instructions in your own words** as complete, readable prose —
  never copy the source text verbatim. Match the voice of existing recipes
  (see `data/recipes/chimichurri.json` for a good example).
- `notes` = things a cook must read before starting (sourcing,
  substitutions, warnings). `endnotes` = storage, serving suggestions,
  background. In the side-by-side layout, notes share the left column with
  the ingredients — more than ~3 short notes risks overflow, so push
  anything non-essential to `endnotes`. Structured substitutions can go in
  `variations` instead.

## 3. Validate and render

```sh
python3 .claude/skills/add-recipe/validate.py data/recipes/<slug>.json
python3 recipe_book/check_glyphs.py
python3 recipe_book/recipe_to_pdf.py data/recipes/<slug>.json --theme print --layout sidebyside
```

Fix and re-run until all three pass. Then use the **preview-pdf** skill to
render the PDF and visually inspect it: look for column overflow, orphaned
headers, and missing-glyph boxes.

## 4. Renaming an existing recipe

Changing a recipe's `title` after the fact needs a few extra steps beyond
editing the field, because the filename, the rendered PDF, and the Drive
copies of both all need to follow:

1. Update the `title` field in the JSON.
2. Rename the file to match the new slug:
   `git mv data/recipes/<old-slug>.json data/recipes/<new-slug>.json`
   (`data/` is gitignored, but `git mv` still works fine as a plain rename).
3. Check for dangling references — books and menus point at recipes by
   filename stem (a book's `recipes[].file`, a menu dish's `file`), not by
   title, so a rename orphans any reference to the old slug:
   `grep -rl '"<old-slug>"' data/books/ data/menus/`. Update the `file`
   value in every match to `<new-slug>`, then re-validate and re-render
   that book/menu (`book_to_pdf.py` / `menu_to_pdf.py`).
4. Re-run validate/glyph-check/render (step 3 above) against the new
   recipe filename, then delete the stale PDF at
   `output/recipes/<old-slug>.pdf`.
5. Preview the new recipe PDF (and any book/menu PDFs touched in step 3)
   with the **preview-pdf** skill.
6. After backing up and publishing (step 5 below), also run
   `./scripts/drive_backup.sh prune` and `./scripts/publish.sh prune` to
   remove the old-named copies from Drive — both list what's stale and ask
   for confirmation before deleting anything.

## 5. Wrap up

`data/recipes/` is gitignored and private — there is nothing to commit. Remind
the user that `./scripts/drive_backup.sh backup` is the only safety net for
the new file, and offer `./scripts/publish.sh` to copy the PDF to Google
Drive.
