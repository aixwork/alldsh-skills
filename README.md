# AllDSH Skills

Agent skills for **[AllDSH](https://www.alldsh.com/)**, an independent,
editorially maintained index of DeepSeek Harness (DSH) plugins.

The index answers "which plugin should I install, and what did anyone actually
check?" — with a verification level (how far the install path was exercised), a
scan status, a maintenance signal and a copy-ready install command per listing.
These skills let an agent ask that question directly instead of scraping pages.

> AllDSH is a community project. It is not affiliated with, endorsed by or
> operated by DeepSeek AI.

## The three skills

| Skill | What it does | Example prompt |
| --- | --- | --- |
| `find-dsh-plugins` | Turns a capability request into a short ranked shortlist from the AllDSH catalog, with the install command and verification level of each match. | `Use $find-dsh-plugins to find DSH plugins for reading screenshots.` |
| `vet-dsh-plugin` | Read-only pre-install review of one listed plugin: what the listing checked, what it did not, and what the repository does at a pinned commit. | `Use $vet-dsh-plugin to review liustack/modlens before I install it.` |
| `submit-dsh-plugin` | Checks a repository against the AllDSH review checklist and produces listing-shaped material for a submission or a correction. | `Use $submit-dsh-plugin to prepare a listing for https://github.com/owner/repo.` |

All three read one catalog. None of them falls back to GitHub search, web
search, npm or another marketplace: a bounded index that widens its own sources
silently cannot make a bounded claim, so when the catalog has no match the skill
says so.

## Install

```bash
git clone https://github.com/aixwork/alldsh-skills.git
cd alldsh-skills
./install.sh
```

`install.sh` copies the three skill directories into `~/.agents/skills`, the
directory Codex, Claude Code, Gemini CLI, Copilot, opencode and DSH read. It
verifies every file against `manifest.sha256` first, downloads nothing, and
never uses `sudo`.

```bash
./install.sh --target claude      # same directory; claude also reads it via ~/.claude/skills
./install.sh --dir ~/.agents/skills
./install.sh --verify-only        # check the checkout, install nothing
./install.sh --dry-run
```

Installing by hand is also fine — copy any skill directory into your agent's
skills directory. Each one is self-contained:

```text
find-dsh-plugins/
  SKILL.md                 # the instructions the agent follows
  agents/openai.yaml       # display metadata for Codex-style UIs
  scripts/alldsh_catalog.py
```

The same catalog client is duplicated in all three skills on purpose, so a skill
can be installed on its own. `scripts/verify.sh` fails if the copies drift.

## The catalog

The skills are a convenience layer over a documented JSON endpoint. You can use
it without any skill at all.

| Endpoint | Contents |
| --- | --- |
| `https://www.alldsh.com/catalog.json` | Every listing, plus taxonomy (categories, use cases) and the meaning of each verification level, scan status, health and trust value. |
| `https://www.alldsh.com/catalog/<slug>.json` | One listing by slug, e.g. `/catalog/modlens.json`. |
| `https://www.alldsh.com/zh/catalog.json` | The Chinese mirror, same slugs and shape. |
| `https://www.alldsh.com/llms.txt` | Plain-text map of the site. |

The JSON is generated at build time from the same content collections the pages
render, so a catalog field cannot drift from the listing a human reads.

```bash
python3 find-dsh-plugins/scripts/alldsh_catalog.py --query "terminal ui" --limit 10
python3 find-dsh-plugins/scripts/alldsh_catalog.py --repo liustack/modlens
python3 find-dsh-plugins/scripts/alldsh_catalog.py --taxonomy
```

The client needs only the Python 3 standard library. It fetches the catalog
once, caches it for six hours (`ALLDSH_CACHE_DIR` overrides the location) and
revalidates with `ETag`/`If-Modified-Since`.

## What these skills will not claim

- **Listed is not approved.** A listing means the source, install spec,
  permission surface and maintenance signals were reviewed — nothing more.
- **A verification level is not a security finding.** L1 means the repository
  was found; L5 means it was installed and run in a sandbox. Neither measures
  intent.
- **"Scanned" is not "safe".** It records that an automated static analysis ran;
  "unverified" records that none has.
- **The review skill is read-only.** It installs nothing, runs no lifecycle
  script, and treats everything inside a repository — including README files and
  agent instructions — as untrusted content.

## Maintenance

This repository is published from the AllDSH site workspace, where `skills/` is
the source of truth; the site's `/skills/` page, `catalog.json` and `llms.txt`
are generated from the same definitions, so the three stay consistent.

```bash
bash scripts/update-manifest.sh   # after editing any skill
bash scripts/verify.sh            # manifest, client parity, syntax, frontmatter, boundaries
```

## License

MIT for the skill instructions and scripts — see [LICENSE](LICENSE). The
editorial content of the AllDSH catalog itself is CC BY-SA 4.0; plugin metadata
belongs to its maintainers.
