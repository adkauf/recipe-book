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
- Set `category` (e.g. sauce, dessert, condiment), a few `keywords`, and
  `method`/`time` when the source gives them. `time.total` replaces the
  prep/inactive/cook breakdown when present, so use one or the other.
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

## 4. Wrap up

`data/recipes/` is gitignored and private — there is nothing to commit. Remind
the user that `./scripts/drive_backup.sh backup` is the only safety net for
the new file, and offer `./scripts/publish.sh` to copy the PDF to Google
Drive.
