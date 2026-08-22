#!/bin/sh
# Back up or restore the private data/ directories (recipes, books, menus,
# images) to/from Google Drive via the ChromeOS Drive mount. The Drive copy
# stays flat (Recipe Book/recipes, ...) so older backups restore unchanged.
#
# ChromeOS mounts Google Drive into the Linux container once it is shared:
# Files app -> right-click "Google Drive" -> "Share with Linux".
#
# Usage:
#   ./scripts/drive_backup.sh backup    # copy local -> Drive (adds/updates only)
#   ./scripts/drive_backup.sh restore   # copy Drive -> local (adds/updates only)
#   ./scripts/drive_backup.sh prune     # list and, on confirmation, delete
#                                        # Drive files no longer present locally
#
# backup and restore never delete files on their target side — they only add
# or update. A file removed locally (accidentally or on purpose) is left
# alone in the Drive backup until you explicitly run prune and confirm.
set -u
cd "$(dirname "$0")/.."

dest="${RECIPE_BACKUP_DIR:-/mnt/chromeos/GoogleDrive/MyDrive/Recipe Book}"
DIRS="recipes books images menus"

usage() {
    echo "usage: $0 backup|restore|prune" >&2
    echo "  backup location: ${dest} (override with RECIPE_BACKUP_DIR)" >&2
    exit 2
}

[ $# -eq 1 ] || usage
cmd=$1

if [ ! -d /mnt/chromeos/GoogleDrive ]; then
    echo "Google Drive is not shared with Linux."
    echo "In the ChromeOS Files app, right-click 'Google Drive' and choose 'Share with Linux', then re-run."
    exit 1
fi

case "${cmd}" in
    backup)
        if ! mkdir -p "${dest}"; then
            echo "Cannot create ${dest}." >&2
            echo "If only some Drive folders are shared with Linux, the MyDrive root is read-only." >&2
            echo "Either share all of Google Drive with Linux, or create the backup folder in Drive," >&2
            echo "share it with Linux, and point RECIPE_BACKUP_DIR at it." >&2
            exit 1
        fi
        for d in ${DIRS}; do
            if [ ! -d "data/${d}" ]; then
                echo "Skipping data/${d}/ (not present locally)"
                continue
            fi
            echo "Backing up data/${d}/ -> ${dest}/${d}"
            mkdir -p "${dest}/${d}" || exit 1
            cp -r "data/${d}/." "${dest}/${d}/" || exit 1
        done
        ;;
    restore)
        for d in ${DIRS}; do
            if [ ! -d "${dest}/${d}" ]; then
                echo "Skipping data/${d}/ (no backup found at ${dest}/${d})"
                continue
            fi
            echo "Restoring ${dest}/${d} -> data/${d}/"
            mkdir -p "data/${d}"
            cp -r "${dest}/${d}/." "data/${d}/" || exit 1
        done
        ;;
    prune)
        tmp_local=$(mktemp)
        tmp_backup=$(mktemp)
        trap 'rm -f "${tmp_local}" "${tmp_backup}"' EXIT

        found=0
        for d in ${DIRS}; do
            [ -d "data/${d}" ] && [ -d "${dest}/${d}" ] || continue
            (cd "data/${d}" && find . -type f | sort) >"${tmp_local}"
            (cd "${dest}/${d}" && find . -type f | sort) >"${tmp_backup}"
            stale=$(comm -13 "${tmp_local}" "${tmp_backup}")
            if [ -n "${stale}" ]; then
                found=1
                echo "Stale in ${dest}/${d} (not present in data/${d}):"
                echo "${stale}" | sed "s|^\./|  ${dest}/${d}/|"
            fi
        done

        if [ "${found}" -eq 0 ]; then
            echo "No stale backup files found."
            exit 0
        fi

        printf 'Delete the files listed above from the Drive backup? [y/N] '
        read -r ans <"$(tty)" || ans=""
        case "${ans}" in
            y|Y|yes|YES) ;;
            *)
                echo "Aborted; no files deleted."
                exit 0
                ;;
        esac

        for d in ${DIRS}; do
            [ -d "data/${d}" ] && [ -d "${dest}/${d}" ] || continue
            (cd "data/${d}" && find . -type f | sort) >"${tmp_local}"
            (cd "${dest}/${d}" && find . -type f | sort) >"${tmp_backup}"
            comm -13 "${tmp_local}" "${tmp_backup}" | while IFS= read -r f; do
                rm -f "${dest}/${d}/${f#./}"
            done
        done
        ;;
    *)
        usage
        ;;
esac

echo "Done."
