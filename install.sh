#!/usr/bin/env bash
# AllDSH agent skills installer.
#
# Copies the three skills from this checkout into the skills directory an agent
# already reads, after verifying every file against manifest.sha256. It never
# downloads anything, never uses sudo, and never touches a file outside the
# target directory.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS=(find-dsh-plugins vet-dsh-plugin submit-dsh-plugin)

TARGET="agents"
TARGET_DIR=""
FORCE=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--target <agents|claude|codex|gemini|copilot|opencode|dsh>]
  ./install.sh --dir <absolute-or-home-relative-path>
  ./install.sh --verify-only

Options:
  --target NAME   Install into the directory that agent reads. All of the named
                  targets except claude map to ~/.agents/skills, which is the
                  shared location; claude also maps there on a machine where
                  ~/.claude/skills is a symlink to it.
  --dir PATH      Install into an explicit directory instead.
  --verify-only   Check manifest.sha256 and exit without installing.
  --dry-run       Print what would be copied.
  --force         Replace an existing skill directory without a prompt.

The installer copies only files listed in manifest.sha256.
EOF
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "[ERR] neither sha256sum nor shasum is available" >&2
    exit 1
  fi
}

verify_manifest() {
  [ -f "$REPO_ROOT/manifest.sha256" ] || { echo "[ERR] manifest.sha256 is missing" >&2; exit 1; }
  local failed=0 line expected path actual
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    expected="${line%% *}"
    path="${line##* }"
    if [ ! -f "$REPO_ROOT/$path" ]; then
      echo "[ERR] missing: $path" >&2
      failed=1
      continue
    fi
    actual="$(sha256_file "$REPO_ROOT/$path")"
    if [ "$actual" != "$expected" ]; then
      echo "[ERR] checksum mismatch: $path" >&2
      failed=1
    fi
  done < "$REPO_ROOT/manifest.sha256"
  [ "$failed" -eq 0 ] || { echo "[ERR] manifest verification failed; re-clone the repository" >&2; exit 1; }
  echo "[ok] manifest.sha256 verified ($(grep -c . "$REPO_ROOT/manifest.sha256") files)"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:-}"; shift 2 ;;
    --dir) TARGET_DIR="${2:-}"; shift 2 ;;
    --verify-only) verify_manifest; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "[ERR] unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$TARGET" in
  agents|claude|codex|gemini|copilot|opencode|dsh) ;;
  *) echo "[ERR] unknown target: $TARGET" >&2; usage >&2; exit 2 ;;
esac

if [ -z "$TARGET_DIR" ]; then
  TARGET_DIR="$HOME/.agents/skills"
fi
case "$TARGET_DIR" in
  "~"*) TARGET_DIR="$HOME/${TARGET_DIR#\~}" ;;
esac

verify_manifest

echo "Installing ${#SKILLS[@]} skills into: $TARGET_DIR"
[ "$DRY_RUN" -eq 1 ] || mkdir -p "$TARGET_DIR"

for skill in "${SKILLS[@]}"; do
  src="$REPO_ROOT/$skill"
  dest="$TARGET_DIR/$skill"
  [ -d "$src" ] || { echo "[ERR] missing skill directory: $skill" >&2; exit 1; }

  if [ -e "$dest" ] && [ "$FORCE" -eq 0 ]; then
    printf 'Replace existing %s? [y/N] ' "$dest"
    read -r reply
    case "$reply" in
      y|Y|yes|YES) ;;
      *) echo "  skipped $skill"; continue ;;
    esac
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  would copy $skill -> $dest"
    continue
  fi

  # One directory swap per skill, so an interrupted install cannot leave a
  # half-written skill behind.
  rm -rf "$dest"
  mkdir -p "$dest"
  (cd "$src" && tar cf - .) | (cd "$dest" && tar xf -)
  echo "  installed $skill"
done

cat <<EOF

Done. Skills are read from $TARGET_DIR.
Try: "Use \$find-dsh-plugins to find DSH plugins for reading screenshots."
Catalog: https://www.alldsh.com/catalog.json
EOF
