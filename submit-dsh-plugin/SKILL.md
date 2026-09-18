---
name: submit-dsh-plugin
description: Prepare a DeepSeek Harness plugin repository for submission to the AllDSH directory, or correct an existing listing, by checking the repository against the review checklist, producing the exact fields and listing text a reviewer needs, and filing the submission through the intake API. Use when someone wants their plugin listed, asks what a submission must contain, or needs a listing corrected (提交插件、收录、上架、提交到 AllDSH).
license: MIT. See LICENSE
metadata:
  author: AllDSH
  version: "1.1.0"
  homepage: https://www.alldsh.com/skills/
---

# Prepare and file an AllDSH submission

Turn a repository into either a new-listing request or a correction, and file
it. AllDSH review is human and happens publicly in a submissions issue, but
the intake is an API: this skill assembles the material, checks the mechanical
parts, and files the submission. It does not publish anything itself.

## Check whether it is already listed

Run `python3 scripts/alldsh_catalog.py --repo "owner/repository"` first.

- If it is listed, do not prepare a new listing. Summarise what the entry
  records, ask what is wrong, and prepare a correction instead.
- If it is not listed, continue.

## Run the checklist against the repository

Read the repository (README, `package.json`, LICENSE, any `dsh.bundle.patch` or
manifest) and report each item as pass, fail, or unverified:

1. Public repository with visible commit history.
2. `dsh-plugin` topic set — verify through the GitHub API, do not assume.
3. A LICENSE file at the root; record the SPDX identifier it actually declares.
4. A copy-ready install command in the README, and whether it works as written
   (`dsh plugin --profile <profile> add <spec>`).
5. A declared `dshTarget` naming the harness release the author tested against.
6. Permission surface a reviewer should know about: shell, network, filesystem
   writes, credentials, paid endpoints, or anything unusual.

Never invent a value to fill a field. Stars, license, language and the last
commit date come from the GitHub API; if a call fails, mark the item unverified
rather than guessing.

## Produce the listing text

Get the valid slugs first: `python3 scripts/alldsh_catalog.py --taxonomy`, then
use only `categories[].slug` (1–3) and `useCases[].slug` (0–3) from that output.
Do not create a category.

Emit exactly this shape, leaving out any optional field the repository does not
declare:

```markdown
---
name: <Display name>
tagline: <one sentence, max 200 characters, no trailing period if it reads better without one>
author: <GitHub owner handle>
repo: <https://github.com/owner/repo>
package: <npm package name, if the install spec resolves to one>
install: <exact install command, only if it differs from the default>
categories: [<1-3 slugs from the catalog taxonomy>]
useCases: [<0-3 slugs>]
tags: [<lowercase keywords>]
stars: <from the GitHub API>
forks: <from the GitHub API>
license: <SPDX id from the LICENSE file>
language: <primary language from the GitHub API>
addedAt: <leave for the maintainer to set>
updatedAt: <today, ISO date>
dshTarget: <harness release the author tested against>
verification: L1
security: unverified
health: active
trust: unrated
---

## What it does

<What the plugin does and the problem it solves, in two or three sentences.>

## Key features

- <Concrete capability, not an adjective.>
- <Three to six items.>

## Compatibility notes

<Which harness release it was tested against, what is known to break on older
releases, and any credential or endpoint requirement.>
```

`verification`, `security` and `trust` are assigned by the maintainer during
review. Submit them at their defaults; do not raise them because the repository
looks tidy.

## File the submission

Do not hand the author a list of things to email — submissions are not taken
by email. File the material directly through the intake:

```bash
python3 scripts/submit.py \
  --repo "owner/repo" \
  --tagline "<one sentence, max 200 characters>" \
  --install "<exact install command>" \
  --category <slug> \
  --notes "<credentials, paid endpoints, unusual permissions>" \
  --listing-file <path to the listing markdown above>
```

For a correction to an existing listing, add `--kind correction`.

The script POSTs to `https://www.alldsh.com/api/submit` (override with
`ALLDSH_SUBMIT_URL`). The intake re-checks the mechanical items itself — the
repository must be public, unarchived and carry the `dsh-plugin` topic — and
answers in JSON:

- `201` with an `issue` URL: filed. Give the author that URL; review happens
  publicly in that issue, usually within a week, and the verdict stays visible
  there either way.
- `409 already_submitted`: an open submission for the repository exists.
  Report its issue URL and add any new information there instead of refiling.
- `422 missing_topic`: set the `dsh-plugin` topic on the repository and retry.
  The other 422 answers (`repo_not_found`, `repo_archived`) name their fix in
  the same way.

A missing checklist item gets the submission returned with a note during
review rather than rejected — but the three intake checks above are hard
gates, so run the checklist before filing, not after.

Finally, state what a listing does not mean: it is not an endorsement and not
a security guarantee. If the author wants the plugin install-checked first,
`$vet-dsh-plugin` reviews the code read-only.
