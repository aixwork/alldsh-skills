---
name: find-dsh-plugins
description: Find DeepSeek Harness (DSH) plugins for a described capability using the AllDSH index, and return install commands with each listing's verification level. Use when someone asks which DSH plugin to use, wants alternatives to one they know, or describes an agent capability they need in another language (查找 DSH 插件、推荐插件、这个需求用哪个插件). Queries only the AllDSH catalog at alldsh.com; it never falls back to GitHub search, web search or another marketplace.
license: MIT. See LICENSE
metadata:
  author: AllDSH
  version: "1.0.0"
  homepage: https://www.alldsh.com/skills/
---

# Find DSH plugins

Match a request to plugins that the AllDSH index already lists. Do the semantic
matching yourself; the script only narrows the field.

## Stay inside the catalog

- The only allowed source is `https://www.alldsh.com/catalog.json`, reached
  through `scripts/alldsh_catalog.py`. Do not search GitHub, the web, npm, or
  another directory, and do not guess repository names.
- If the catalog has no match, say so and offer a narrower or differently worded
  request. An empty answer from a bounded index is a real answer; padding it from
  an unbounded search is not.
- If the client fails and has no cached copy, report that and stop.

## Query efficiently

1. Turn the request into one compact query: the core capability plus English
   synonyms (`screenshot`, `image`, `vision`, `ocr`). One query per task.
2. Run from this skill directory:

   ```bash
   python3 scripts/alldsh_catalog.py --query "<capability and synonyms>" --limit 20
   ```

   Add a filter only when the user stated the constraint:
   `--category <slug>`, `--use-case <slug>`, `--min-verification L3`,
   `--security scanned`, `--health active`.
3. `--taxonomy` prints the valid category and use-case slugs plus what L1–L5
   mean. Run it before inventing a filter value.
4. The client fetches once, caches for six hours and revalidates with ETag. Do
   not add cache-busting parameters or download the catalog yourself.

## Rank semantically

1. `lexicalScore` generates candidates. It is not the ranking.
2. Re-rank the returned candidates against the user's actual task using `name`,
   `tagline`, `tags`, `categories`, `useCases` and `language`. Do not require
   literal keyword overlap: "a terminal UI" can match `tui`, `cli` or
   `terminal` when the description supports it.
3. Capability fit comes first. Use `stars` and `updatedAt` only as tie-breakers,
   never as evidence of quality.
4. `verification.level` records how far the install path was exercised and
   `security.status` whether a scan has run. Use them as filters the user asked
   for, not as a quality score you invented.
5. Return three to five strong matches, or fewer when fewer genuinely fit.

## Present each recommendation

For every result give:

- Plugin name and repository URL.
- One sentence tying it to the requested capability — not a restatement of the
  tagline.
- The install command exactly as the catalog gives it (`install` field), in a
  code block.
- The verification level, spelled out from `verification.description`, and the
  scan status from `security.label`.
- `dshTarget` when present, so the user can check it against their harness
  release, and a note if it is missing.
- The listing URL (`page`) so the user can read what was checked.

Then state, in one line: a listing is not an endorsement or a security review,
and stars measure attention rather than quality. Offer `$vet-dsh-plugin` on the
chosen entry before the user installs it.
