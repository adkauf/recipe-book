#!/bin/sh
# Generate all recipes and books. Exits non-zero if anything failed.
set -u
cd "$(dirname "$0")/.."

layout="sidebyside"
theme="print"

echo "Generating all recipes and books using these options:"
echo " Layout: ${layout}"
echo " Theme: ${theme}"

# Pre-flight: every character must have a glyph in the font that renders it.
python3 recipe_book/check_glyphs.py || exit 1

failures=0

rc=0
for recipe in recipes/*.json; do
    [ -e "${recipe}" ] || continue
    if python3 recipe_book/recipe_to_pdf.py "${recipe}" --theme "${theme}" --layout "${layout}"; then
        rc=$((rc + 1))
    else
        echo "FAILED: ${recipe}" >&2
        failures=$((failures + 1))
    fi
done
echo "Wrote ${rc} recipes."

bc=0
for book in books/*.json; do
    [ -e "${book}" ] || continue
    if python3 recipe_book/book_to_pdf.py "${book}" --theme "${theme}" --layout "${layout}"; then
        bc=$((bc + 1))
    else
        echo "FAILED: ${book}" >&2
        failures=$((failures + 1))
    fi
done
echo "Wrote ${bc} books."

if [ "${failures}" -gt 0 ]; then
    echo "${failures} generation(s) failed." >&2
    exit 1
fi
