---
name: scale-recipe
description: Create a reduced- or increased-portion version of an existing library recipe as a new file, rescaling amounts with cook's judgment rather than blind arithmetic. Use when the user wants a recipe "for one", "for two", halved, doubled, or scaled to a specific serving count.
---

# Scale a recipe

Turn an existing `data/recipes/<slug>.json` into a new sibling file at a
different serving count. Unlike add-recipe, nothing is imported — the
source is already in the library. Unlike compose-book, this produces a
recipe, not a book.

The original file is never touched: other books may depend on its current
servings and amounts. Scaling always produces a **new** file.

## 1. Resolve the source and target

Confirm which existing recipe (`ls data/recipes/`) and target serving
count/description the user means ("for two", "halved", "8 servings").

**Never infer the target.** If the user didn't say what to scale to, ask
before writing anything — there is no default. The ratio is a cooking
decision, and guessing it wastes the whole rescale. Surrounding context
(e.g. "for the two-person book") narrows the range but is not an answer:
confirm the actual serving count. Read the original's current `servings`/
`yield` first so you can ask concretely ("this serves 6 — scale to 2?").

If the recipe has multiple components sharing implicit totals (e.g. a
sauce component and a main component), scale all components consistently
unless the user says otherwise.

## 2. Naming and title

- New filename: `<original-slug>-for-two` (or `-for-one`, `-halved`,
  `-doubled`, `-for-<n>` — pick whatever reads clearly for the target;
  ask if it's not obvious).
- **Title stays identical to the original** — don't append "(For Two)" or
  similar to the printed title. Any framing that this is a reduced
  portion belongs in the book's own front matter/notes, not baked into
  every recipe title.
- Set `servings` (or `yield`) to the new target. For a `yield` recipe
  (sauces, condiments) restate the measure itself — "1 pint" → "1 cup" —
  since there's no separate count to carry the change.
- **Do not scale `serving_size`.** It describes one portion, which is
  exactly what stays fixed while the count changes. Scaling both
  double-counts the reduction: 6 × 1 cup dropped to 2 × ⅓ cup is a sixth
  of the original, not a third. Change it only if the user actually wants
  a different portion size, which is a separate request from scaling.

## 3. Rescale amounts — judgment, not a divide script

Compute the raw ratio (target ÷ original) as a *starting point* only,
then rewrite each ingredient by hand:

- **Round to sensible kitchen quantities.** ¼ cup scaled by 1/3 is not
  "0.083 cup" — it's "1 tablespoon" or whatever a person would actually
  measure. Keep using Unicode vulgar fractions (¼ ½ ¾ ⅓ ⅔ ⅛), never
  decimals or "1/4".
- **Respect real minimums.** Eggs, garlic cloves, and similar discrete
  ingredients often can't scale linearly — "3 eggs → 1 egg" not
  "0.75 eggs". Where a fractional unit is genuinely needed (half an egg),
  say so explicitly (e.g. "1 egg, beaten, half reserved") rather than
  printing a fraction that isn't measurable. When a scaled amount would
  round to something silly, consider `descriptor` ("to taste", "as
  needed") only if the ingredient genuinely tolerates that — don't use it
  to dodge a hard scaling call on something that matters (e.g. leavening,
  brine salt).
- **Re-check instructions, not just ingredients.** Pan/dish size, cook
  time, and yield-dependent steps ("divide into two portions", "fills a
  9x13 pan") often need rewording for the new scale — a smaller mass in
  the same pan browns faster or a recipe for 2 needs a smaller pan
  entirely. Rewrite affected steps; don't leave stale quantities in prose.
- **Carry `source` over unchanged.** Scaling isn't a change to the
  external source relationship, so don't flip `source.adapted` just for
  this. Instead add a `notes` entry noting the scaling, e.g. "Scaled down
  from the full recipe, which serves 6." — this also tells a reader why a
  near-identical file exists alongside the original.
- Everything else (category, method, cuisine, keywords, time) carries
  over from the original unless the scale genuinely changes it (e.g.
  `time.cook` shortening for a smaller batch).

## 4. Validate and render

```sh
python3 .claude/skills/add-recipe/validate.py data/recipes/<new-slug>.json
python3 recipe_book/check_glyphs.py
python3 recipe_book/recipe_to_pdf.py data/recipes/<new-slug>.json --theme print --layout sidebyside
```

Fix and re-run until all three pass. Then use **preview-pdf** to check the
rendered PDF, same as after add-recipe.

## 5. Wrap up

The new file lives in the shared library (`data/recipes/`), available to
any book — not just the one that prompted it. It does not touch the
original recipe or any book currently referencing it. Remind the user
`./scripts/drive_backup.sh backup` is the safety net for the new file.
