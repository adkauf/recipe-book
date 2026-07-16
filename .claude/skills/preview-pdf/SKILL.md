---
name: preview-pdf
description: Render pages of a generated PDF to PNG images for visual inspection. Use after any layout, theme, or style change, after adding a recipe, or whenever you need to see how a PDF actually looks before declaring work done.
---

# Preview a PDF

PDFs in `output/` can't be judged from the terminal. Render pages to PNG
with `pdftoppm` (poppler-utils), then Read the images to inspect them.

## Render

```sh
pdftoppm -png -r 100 output/<name>.pdf "$SCRATCHPAD/<name>"
```

Use the session scratchpad directory for the images — they are throwaway.
This writes `<name>-1.png`, `<name>-2.png`, … (page numbers are padded to
equal width when there are 10+ pages). 100 dpi is enough for layout
checks; use `-r 150` when judging fine typography, and `-f N -l N` to
render only page N of a long book.

## Inspect

Read each PNG and check:

- Text overflowing or crowding its column or frame (side-by-side layout:
  the left ingredients/notes column is the usual victim).
- Missing-glyph boxes (▯/□) — if seen, run
  `python3 recipe_book/check_glyphs.py` to identify the character.
- Orphaned section headers at a page bottom; widowed single lines.
- Margins, alignment, and consistent spacing between sections.

Iterate on the change and re-render until the page looks right. Do not
report a layout or theme change as done without having looked at the
rendered output.

## Show the user

For visual changes the user should sign off on (new theme, new style,
spacing changes), send the relevant PNG(s) with SendUserFile so they can
see the result without opening the PDF.
