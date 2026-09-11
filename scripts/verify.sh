#!/usr/bin/env bash
# Repository self-check. Run before committing: it catches the two failures this
# layout makes possible — a client copy that drifted from its siblings, and a
# SKILL.md whose frontmatter name does not match the directory an agent installs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS=(find-dsh-plugins vet-dsh-plugin submit-dsh-plugin)
failures=0

pass() { echo "[ok] $*"; }
fail() { echo "[ERR] $*" >&2; failures=$((failures + 1)); }

# 1. Manifest
if [ -f "$REPO_ROOT/manifest.sha256" ]; then
  ( cd "$REPO_ROOT" && bash ./install.sh --verify-only >/dev/null ) \
    && pass "manifest.sha256 matches the working tree" \
    || fail "manifest.sha256 is stale — run scripts/update-manifest.sh"
else
  fail "manifest.sha256 is missing"
fi

# 2. The catalog client is byte-identical in all three skills, because each
#    skill directory has to be installable on its own.
reference="$REPO_ROOT/find-dsh-plugins/scripts/alldsh_catalog.py"
for skill in "${SKILLS[@]}"; do
  candidate="$REPO_ROOT/$skill/scripts/alldsh_catalog.py"
  if [ ! -f "$candidate" ]; then
    fail "$skill/scripts/alldsh_catalog.py is missing"
  elif ! cmp -s "$reference" "$candidate"; then
    fail "$skill/scripts/alldsh_catalog.py differs from find-dsh-plugins copy"
  fi
done
pass "catalog client copies are identical"

# 3. Python syntax
if command -v python3 >/dev/null 2>&1; then
  for skill in "${SKILLS[@]}"; do
    python3 -m py_compile "$REPO_ROOT/$skill/scripts/alldsh_catalog.py" \
      || fail "$skill client does not compile"
  done
  rm -rf "$REPO_ROOT/find-dsh-plugins/scripts/__pycache__" \
         "$REPO_ROOT/vet-dsh-plugin/scripts/__pycache__" \
         "$REPO_ROOT/submit-dsh-plugin/scripts/__pycache__"
  pass "catalog clients compile"
else
  echo "[skip] python3 not found; syntax check skipped"
fi

# 4. Frontmatter name matches the directory, and description exists.
for skill in "${SKILLS[@]}"; do
  file="$REPO_ROOT/$skill/SKILL.md"
  [ -f "$file" ] || { fail "$skill/SKILL.md is missing"; continue; }
  name="$(awk -F': *' '/^name:/{print $2; exit}' "$file")"
  [ "$name" = "$skill" ] || fail "$skill/SKILL.md declares name: ${name:-<none>}"
  grep -q '^description: ' "$file" || fail "$skill/SKILL.md has no description"
done
pass "SKILL.md frontmatter matches directories"

# 5. No agent instructions outside the skills point at a second registry. The
#    scan covers what an agent actually reads (the skill directories plus the
#    installer); scripts/ is excluded because this file has to name the pattern
#    it is looking for.
scan_targets=()
for skill in "${SKILLS[@]}"; do scan_targets+=("$REPO_ROOT/$skill"); done
scan_targets+=("$REPO_ROOT/install.sh")
[ -f "$REPO_ROOT/README.md" ] && scan_targets+=("$REPO_ROOT/README.md")
[ -f "$REPO_ROOT/README.zh-CN.md" ] && scan_targets+=("$REPO_ROOT/README.zh-CN.md")
if grep -RIn -E 'dshplugin\.(org|app)|awesome-dsh|dsh-plugin-hub' "${scan_targets[@]}" >/dev/null 2>&1; then
  fail "a skill references another registry; these skills must stay bounded to alldsh.com"
else
  pass "no references to other registries"
fi

if [ "$failures" -gt 0 ]; then
  echo "" >&2
  echo "$failures check(s) failed" >&2
  exit 1
fi
echo ""
echo "All checks passed."
