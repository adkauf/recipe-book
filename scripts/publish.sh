#!/bin/sh
# Publish generated PDFs to Google Drive.
#
# ChromeOS mounts Google Drive into the Linux container once it is shared:
# Files app -> right-click "Google Drive" -> "Share with Linux".
# After that, copying to the mount below syncs to Drive automatically.
set -u
cd "$(dirname "$0")/.."

dest="${RECIPE_PUBLISH_DIR:-/mnt/chromeos/GoogleDrive/MyDrive/Recipes}"

if [ ! -d /mnt/chromeos/GoogleDrive ]; then
    echo "Google Drive is not shared with Linux."
    echo "In the ChromeOS Files app, right-click 'Google Drive' and choose 'Share with Linux', then re-run."
    exit 1
fi

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
