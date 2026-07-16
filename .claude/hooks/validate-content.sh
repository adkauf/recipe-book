#!/bin/sh
# PostToolUse hook: after a Write/Edit to a recipes/, books/, or menus/
# JSON file, validate it against its schema and re-run the glyph check.
# Exit 2 feeds the validation errors back to Claude so it fixes them.
set -u
cd "$(dirname "$0")/../.."

file=$(python3 -c 'import json, sys
print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))')
case "${file}" in
    */recipes/*.json | */books/*.json | */menus/*.json) ;;
    *) exit 0 ;;
esac
[ -e "${file}" ] || exit 0

python3 .claude/skills/add-recipe/validate.py "${file}" >/dev/null || exit 2
python3 recipe_book/check_glyphs.py >/dev/null || exit 2
