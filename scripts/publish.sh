#!/bin/sh
# Publish generated PDFs to Google Drive.
#
# ChromeOS mounts Google Drive into the Linux container once it is shared:
# Files app -> right-click "Google Drive" -> "Share with Linux".
# After that, copying to the mount below syncs to Drive automatically.
#
# Usage:
#   ./scripts/publish.sh          # copy output/*/*.pdf to Drive (adds/updates only)
#   ./scripts/publish.sh publish  # same as above, explicit form
#   ./scripts/publish.sh prune    # list and, on confirmation, delete
#                                  # published PDFs no longer present in output/
#
# publish never deletes files at the destination — it only adds or updates.
# A PDF removed or renamed locally (e.g. after renaming a recipe) is left
# alone in the published Drive folder until you explicitly run prune and
# confirm.
set -u
cd "$(dirname "$0")/.."

dest="${RECIPE_PUBLISH_DIR:-/mnt/chromeos/GoogleDrive/MyDrive/Recipes}"
SUBS="recipes books menus"

usage() {
    echo "usage: $0 [publish|prune]" >&2
    echo "  publish location: ${dest} (override with RECIPE_PUBLISH_DIR)" >&2
    exit 2
}

[ $# -le 1 ] || usage
cmd="${1:-publish}"

if [ ! -d /mnt/chromeos/GoogleDrive ]; then
    echo "Google Drive is not shared with Linux."
    echo "In the ChromeOS Files app, right-click 'Google Drive' and choose 'Share with Linux', then re-run."
    exit 1
fi

case "${cmd}" in
    publish)
        mkdir -p "${dest}"
        pc=0
        for pdf in output/*/*.pdf
        do
            [ -e "${pdf}" ] || continue
            sub=$(basename "$(dirname "${pdf}")")
            mkdir -p "${dest}/${sub}"
            cp "${pdf}" "${dest}/${sub}/"
            pc=$((pc += 1))
        done
        echo "Published ${pc} PDFs to ${dest} (mirroring output/)"
        ;;
    prune)
        tmp_local=$(mktemp)
        tmp_dest=$(mktemp)
        trap 'rm -f "${tmp_local}" "${tmp_dest}"' EXIT

        found=0
        for sub in ${SUBS}; do
            [ -d "${dest}/${sub}" ] || continue
            (cd "output/${sub}" 2>/dev/null && find . -maxdepth 1 -type f -name '*.pdf' | sort) >"${tmp_local}"
            (cd "${dest}/${sub}" && find . -maxdepth 1 -type f -name '*.pdf' | sort) >"${tmp_dest}"
            stale=$(comm -13 "${tmp_local}" "${tmp_dest}")
            if [ -n "${stale}" ]; then
                found=1
                echo "Stale in ${dest}/${sub} (not present in output/${sub}):"
                echo "${stale}" | sed "s|^\./|  ${dest}/${sub}/|"
            fi
        done

        if [ "${found}" -eq 0 ]; then
            echo "No stale published PDFs found."
            exit 0
        fi

        printf 'Delete the files listed above from the published Drive folder? [y/N] '
        read -r ans <"$(tty)" || ans=""
        case "${ans}" in
            y|Y|yes|YES) ;;
            *)
                echo "Aborted; no files deleted."
                exit 0
                ;;
        esac

        for sub in ${SUBS}; do
            [ -d "${dest}/${sub}" ] || continue
            (cd "output/${sub}" 2>/dev/null && find . -maxdepth 1 -type f -name '*.pdf' | sort) >"${tmp_local}"
            (cd "${dest}/${sub}" && find . -maxdepth 1 -type f -name '*.pdf' | sort) >"${tmp_dest}"
            comm -13 "${tmp_local}" "${tmp_dest}" | while IFS= read -r f; do
                rm -f "${dest}/${sub}/${f#./}"
            done
        done
        echo "Done."
        ;;
    *)
        usage
        ;;
esac
