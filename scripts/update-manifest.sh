#!/usr/bin/env bash
# Regenerate manifest.sha256 from the skill directories.
#
# The manifest covers the files an install copies (the three skill directories),
# not the repository's own README, LICENSE or installer: those are read in place
# before the install starts, so a change to them cannot invalidate an installed
# skill.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

: > manifest.sha256
find find-dsh-plugins vet-dsh-plugin submit-dsh-plugin -type f \
  ! -name '*.pyc' ! -path '*__pycache__*' | LC_ALL=C sort | while IFS= read -r path; do
  printf '%s  %s\n' "$(sha256_file "$path")" "$path" >> manifest.sha256
done

echo "manifest.sha256 updated: $(grep -c . manifest.sha256) files"
