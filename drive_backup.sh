#!/bin/sh
# Back up or restore the private recipes/, books/, and images/ directories
# to/from Google Drive using rclone.
#
# One-time setup:
#   1. Install rclone: https://rclone.org/install/
#   2. Run `rclone config` and create a Google Drive remote named "gdrive"
#      (or any name — pass it as the second argument or set
#      RECIPE_BACKUP_REMOTE).
#
# Usage:
#   ./drive_backup.sh backup  [remote:path]   # mirror local -> Drive
#   ./drive_backup.sh restore [remote:path]   # copy Drive -> local
#
# backup uses `rclone sync`, so files deleted locally are also removed from
# the Drive copy. restore uses `rclone copy`, which never deletes local
# files — it only adds or updates them.
set -u
cd "$(dirname "$0")"

REMOTE="${RECIPE_BACKUP_REMOTE:-gdrive:recipe-book-backup}"
DIRS="recipes books images"

usage() {
    echo "usage: $0 backup|restore [remote:path]" >&2
    echo "  default remote: ${REMOTE}" >&2
    exit 2
}

[ $# -ge 1 ] || usage
cmd=$1
[ $# -ge 2 ] && REMOTE=$2

if ! command -v rclone >/dev/null 2>&1; then
    echo "Error: rclone not found. Install it and run 'rclone config' to set up a Google Drive remote." >&2
    exit 1
fi

case "${cmd}" in
    backup)
        for d in ${DIRS}; do
            if [ ! -d "${d}" ]; then
                echo "Skipping ${d}/ (not present locally)"
                continue
            fi
            echo "Backing up ${d}/ -> ${REMOTE}/${d}"
            rclone sync "${d}" "${REMOTE}/${d}" --progress || exit 1
        done
        ;;
    restore)
        for d in ${DIRS}; do
            echo "Restoring ${REMOTE}/${d} -> ${d}/"
            rclone copy "${REMOTE}/${d}" "${d}" --progress || exit 1
        done
        ;;
    *)
        usage
        ;;
esac

echo "Done."
