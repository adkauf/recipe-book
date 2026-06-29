#!/bin/sh
# Generate all recipes and books

layout="sidebyside"
theme="print"

echo "Generating all recipes and books using these options:"
echo " Layout: "${layout}
echo " Theme: "${theme}

rc=0
for recipe in `ls recipes/*.json`
do
    python3 recipe_book/recipe_to_pdf.py ${recipe} --theme ${theme} --layout ${layout}
    rc=$((rc += 1))
done
echo "Wrote ${rc} recipes."
bc=0
for book in `ls books/*.json`
do
    python3 recipe_book/book_to_pdf.py ${book} --theme ${theme} --layout ${layout}
    bc=$((bc += 1))
done
echo "Wrote ${bc} books."
