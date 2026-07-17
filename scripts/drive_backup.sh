#!/bin/sh
# Back up or restore the private data/ directories (recipes, books, menus,
# images) to/from Google Drive via the ChromeOS Drive mount. The Drive copy
# stays flat (Recipe Book/recipes, ...) so older backups restore unchanged.
#
# ChromeOS mounts Google Drive into the Linux container once it is shared:
# Files app -> right-click "Google Drive" -> "Share with Linux".
#
# Usage:
#   ./scripts/drive_backup.sh backup    # mirror local -> Drive
#   ./scripts/drive_backup.sh restore   # copy Drive -> local
#
# backup replaces the Drive copy of each directory wholesale, so files
# deleted locally are also removed from the Drive copy (Drive keeps them
# in its trash for 30 days). restore never deletes local files — it only
# adds or updates them.
set -u
cd "$(dirname "$0")/.."

dest="${RECIPE_BACKUP_DIR:-/mnt/chromeos/GoogleDrive/MyDrive/Recipe Book}"
DIRS="recipes books images menus"

usage() {
    echo "usage: $0 backup|restore" >&2
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
            rm -rf "${dest}/${d}" || exit 1
            cp -r "data/${d}" "${dest}/${d}" || exit 1
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
    *)
        usage
        ;;
esac

echo "Done."
