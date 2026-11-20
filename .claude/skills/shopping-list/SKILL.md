---
name: shopping-list
description: Produce a consolidated, store-ordered shopping-list PDF for one or more library recipes, or for every recipe in a menu or book, merging duplicate ingredients across recipes and converting to purchase units. Use when the user wants a shopping list, grocery list, or "what do I need to buy" for recipes, a menu, or a meal plan.
---

# Make a shopping list

Turn a set of library recipes into `data/shopping-lists/<slug>.json`,
then render it to `output/shopping-lists/<slug>.pdf` and publish it to
Drive. Nothing in `data/recipes/` is changed. Recipes are only read.

## 1. Resolve what to shop for

The user names recipes, a menu (`data/menus/`), a book (`data/books/`),
or a mix. Confirm stems with `ls data/recipes/`. If they name a dish
that isn't in the library, offer **add-recipe** first, or list it as a
plain item if it's store-bought.

Settle the **scale** for each recipe before gathering:

- Default is one batch (×1) for an explicitly named recipe. Don't ask.
- **Menu dish notes** that change quantity ("double the recipe") apply
  directly. Carry them over as a scale.
- **Menu `guests` vs. recipe servings:** if a menu feeds 12 and a main
  serves 6, ask whether to scale. Don't silently double. Sides, sauces,
  and condiments usually don't scale with headcount in a multi-dish meal.
- Explicit numbers from the user ("for 8", "halve the chili") are a
  scale. Compute it from the recipe's `servings`/`yield`.

Menu dishes with only a `name` (e.g. "Cheese board") have no recipe.
Ask whether they need buying and, if so, add them as plain items.

## 2. Gather raw ingredients

```sh
python3 .claude/skills/shopping-list/gather.py <stem>[:scale] ... [data/menus/<x>.json[:scale]] [data/books/<x>.json]
```

It prints each recipe with its scale (and any menu note), then every
ingredient grouped by exact name with its scaled amount and source.
`[descriptor]` amounts are unmeasured ("to taste", "for serving").
Notes marked `[note unscaled]` still show the original numbers. A
stem given explicitly overrides the scale a menu or book gives it.
Amounts the script couldn't parse say "scale by hand".

## 3. Consolidate with judgment

The script only groups identical names. You do the merging:

- **Merge synonyms and forms.** "garlic", "large cloves garlic", and
  "garlic, minced" are one item. So are "all purpose flour" and
  "all-purpose flour". Lime juice and "lime, juiced" become limes.
  Don't merge things that differ at the store: "unsalted butter" vs.
  "salted butter", "fresh thyme" vs. "dried thyme".
- **Convert to purchase units and round up.** Shop the way the store
  sells: garlic cloves → heads (~10 cloves/head), butter tablespoons
  → sticks (8 tbsp) or pounds, eggs → count (or "1 dozen"), herbs →
  bunches, citrus juice → whole fruit (~2 tbsp per lime, ~3 tbsp per
  lemon, ~⅓ cup per orange), flour and sugar → bag size. Canned goods
  stay as `1 (28-ounce) can`.
- **Keep the real need in `note`** when the purchase unit hides it:
  `"quantity": "2 heads", "note": "about 21 cloves"`. For weighed baking
  and fermentation ingredients, always note the gram total
  (`"need 480 grams"`). The cook weighs these, so the precision matters.
- **Unmeasured items** ("to taste", "for frying", "for serving") get no
  `quantity`. Use a note if the amount matters ("for frying, about 2
  quarts"). Drop tap water and ice outright.
- **Sub-recipes:** if one recipe's ingredient is another library recipe
  (a sauce, a stock), ask make-or-buy. "Make" means add that recipe to
  the list. "Buy" means list the store-bought item.
- Fill `recipes` on each item with the stems that use it, so a cook
  who drops a dish knows what to skip.

## 4. Organize into store sections

Use store walking order and omit empty sections:

Produce → Meat & Seafood → Deli & Cheese → Dairy & Eggs → Bakery →
Canned & Jarred → Dry Goods & Pasta → Baking → Spices & Seasonings →
Condiments & Oils → International → Frozen → Beverages & Liquor → Other

End with a **Check the Pantry** section (`"description": "Likely on
hand. Check before you go."`) for staples most kitchens stock: salt,
pepper, cooking oil, common dried spices, flour, sugar, baking powder
and soda, vinegar, soy sauce. Include quantities so the cook can check
the jar actually has enough. Anything the user says they have on hand
stays off the list entirely. Note that in `notes` if it's significant
("Assumes turkey is already purchased").

Within a section, order items roughly by how the cook shops it
(produce: aromatics, vegetables, herbs, fruit), not alphabetically.

## 5. Write the JSON

`schema/shopping-list.json` is the source of truth. House conventions:

- First key is `"$schema": "../../schema/shopping-list.json"`; 4-space
  indent.
- Slug: the menu or book stem when shopping for one
  (`thanksgiving-dinner`). Otherwise something descriptive
  (`adobo-and-rice`). Check `ls data/shopping-lists/` and update an
  existing list rather than creating a near-duplicate.
- `title`: the occasion or menu title. `date`: when the food is needed,
  if known (copy a menu's `date`).
- `recipes`: every recipe shopped for, with `scale` when it isn't 1.
  Every item's `recipes` entry must name one of these, and the renderer
  rejects strays.
- Quantities use Unicode vulgar fractions (¼ ½ ¾ ⅓ ⅔), spelled-out units,
  lowercase ingredient names except proper nouns. Same as recipes.

The PostToolUse hook validates the file and re-runs the glyph check on
every write.

## 6. Render, preview, publish

```sh
python3 .claude/skills/add-recipe/validate.py data/shopping-lists/<slug>.json
python3 recipe_book/shopping_list_to_pdf.py data/shopping-lists/<slug>.json --theme print
```

Use **preview-pdf** to check it. Make sure check boxes line up with the
first line of each item, no section header is stranded at a column
bottom, and both columns are balanced.

Then run `./scripts/publish.sh`. It only adds or updates, never
deletes, and the PDF lands in `MyDrive/Recipes/shopping-lists/` for the
user's phone. Give the user a short summary: item count by section and
any judgment calls you made (scales, make-or-buy, what you assumed on
hand). Remind them `./scripts/drive_backup.sh backup` covers the new
JSON.
