#!/usr/bin/env python3
"""Query the AllDSH catalog. One network origin, one cached copy, no fallbacks.

This client exists so that a skill does not have to scrape the website or hold a
catalog in its context. It fetches https://www.alldsh.com/catalog.json, caches
it for six hours, revalidates with ETag/Last-Modified, and prints a short JSON
candidate set that the agent then re-ranks semantically.

Two properties are deliberate:

*   The single allowed origin is hard-coded. There is no flag to point this at
    another registry, a GitHub search, or a mirror, because a lookup that can
    silently widen its own sources cannot make a bounded claim about coverage.
*   Every failure mode either uses the cached copy or raises. It never returns a
    partial answer that looks complete.
"""

import argparse
import gzip
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CATALOG_URL = "https://www.alldsh.com/catalog.json"
USER_AGENT = "alldsh-agent-skill/1.0 (+https://www.alldsh.com/skills/)"
CACHE_TTL_SECONDS = 6 * 60 * 60
MAX_TRANSFER_BYTES = 8 * 1024 * 1024
MAX_CATALOG_BYTES = 32 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"[\w.+#-]+", re.UNICODE)

CACHE_ROOT = Path(
    os.environ.get("ALLDSH_CACHE_DIR") or (Path(tempfile.gettempdir()) / "alldsh-agent-cache")
)
CACHE_FILE = CACHE_ROOT / "catalog.json"
METADATA_FILE = CACHE_ROOT / "catalog.meta.json"

VERIFICATION_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
PUBLIC_FIELDS = (
    "slug",
    "name",
    "tagline",
    "repo",
    "package",
    "install",
    "categories",
    "useCases",
    "tags",
    "stars",
    "license",
    "language",
    "dshTarget",
    "verification",
    "security",
    "health",
    "trust",
    "featured",
    "editorsChoice",
    "updatedAt",
    "page",
    "catalog",
    "pageAlt",
)


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def write_json(path, value):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def validate_catalog(catalog):
    if not isinstance(catalog, dict):
        raise RuntimeError("catalog payload is not an object")
    if not isinstance(catalog.get("plugins"), list):
        raise RuntimeError("catalog payload has no plugins array")
    for plugin in catalog["plugins"]:
        if not isinstance(plugin, dict) or not plugin.get("slug"):
            raise RuntimeError("catalog contains a listing without a slug")
    return catalog


def fetch_catalog():
    """Return the catalog, preferring a fresh cache and revalidating when stale."""
    cached = read_json(CACHE_FILE)
    metadata = read_json(METADATA_FILE) or {}
    fetched_at = float(metadata.get("fetchedAt") or 0)
    if cached is not None and time.time() - fetched_at < CACHE_TTL_SECONDS:
        return validate_catalog(cached)

    headers = {"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": USER_AGENT}
    if cached is not None and metadata.get("etag"):
        headers["If-None-Match"] = metadata["etag"]
    if cached is not None and metadata.get("lastModified"):
        headers["If-Modified-Since"] = metadata["lastModified"]

    try:
        with urlopen(Request(CATALOG_URL, headers=headers), timeout=30) as response:
            payload = response.read(MAX_TRANSFER_BYTES + 1)
            if len(payload) > MAX_TRANSFER_BYTES:
                raise RuntimeError("catalog transfer exceeded the safety limit")
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                payload = gzip.decompress(payload)
            if len(payload) > MAX_CATALOG_BYTES:
                raise RuntimeError("catalog exceeded the safety limit")
            catalog = validate_catalog(json.loads(payload.decode("utf-8")))
            write_json(CACHE_FILE, catalog)
            write_json(
                METADATA_FILE,
                {
                    "etag": response.headers.get("ETag", ""),
                    "lastModified": response.headers.get("Last-Modified", ""),
                    "fetchedAt": time.time(),
                    "source": CATALOG_URL,
                },
            )
            return catalog
    except HTTPError as error:
        if error.code == 304 and cached is not None:
            metadata["fetchedAt"] = time.time()
            write_json(METADATA_FILE, metadata)
            return validate_catalog(cached)
        if cached is not None:
            print(
                f"warning: using the cached catalog after HTTP {error.code}",
                file=sys.stderr,
            )
            return validate_catalog(cached)
        raise RuntimeError(f"catalog request failed with HTTP {error.code}") from error
    except (OSError, ValueError, json.JSONDecodeError) as error:
        if cached is not None:
            print("warning: using the cached catalog after a refresh error", file=sys.stderr)
            return validate_catalog(cached)
        raise RuntimeError(f"catalog is unavailable: {error}") from error


def tokens(value):
    return set(TOKEN_PATTERN.findall(str(value or "").casefold()))


def searchable(plugin):
    return {
        "slug": str(plugin.get("slug") or "").casefold(),
        "name": str(plugin.get("name") or "").casefold(),
        "repo": str(plugin.get("repo") or "").casefold(),
        "package": str(plugin.get("package") or "").casefold(),
        "tagline": str(plugin.get("tagline") or "").casefold(),
        "tags": " ".join(plugin.get("tags") or []).casefold(),
        "categories": " ".join(plugin.get("categories") or []).casefold(),
        "useCases": " ".join(plugin.get("useCases") or []).casefold(),
        "language": str(plugin.get("language") or "").casefold(),
    }


def score_plugin(plugin, query):
    """Lexical candidate generation.

    The score decides what the agent gets to look at; it is not the answer.
    Capability words outweigh popularity words, and stars never contribute, so a
    high-star plugin cannot outrank a better capability match.
    """
    fields = searchable(plugin)
    normalized = query.casefold().strip()
    query_tokens = tokens(normalized)
    score = 0.0
    matched = 0

    if normalized:
        if normalized == fields["repo"] or normalized == fields["slug"]:
            score += 140
        elif normalized == fields["name"]:
            score += 120
        elif normalized in fields["name"] or normalized in fields["tagline"]:
            score += 40

    for term in query_tokens:
        term_score = 0
        if term in fields["name"]:
            term_score += 18
        if term in fields["tags"]:
            term_score += 15
        if term in fields["slug"]:
            term_score += 12
        if term in fields["categories"]:
            term_score += 12
        if term in fields["useCases"]:
            term_score += 12
        if term in fields["tagline"]:
            term_score += 8
        if term in fields["repo"] or term in fields["package"]:
            term_score += 6
        if term in fields["language"]:
            term_score += 3
        if term_score:
            matched += 1
            score += term_score

    if query_tokens:
        score += round(12 * matched / len(query_tokens), 3)
    return score


def matches_filters(plugin, args):
    if args.category and args.category not in (plugin.get("categories") or []):
        return False
    if args.use_case and args.use_case not in (plugin.get("useCases") or []):
        return False
    if args.security and plugin.get("security", {}).get("status") != args.security:
        return False
    if args.health and plugin.get("health") != args.health:
        return False
    if args.min_verification:
        level = (plugin.get("verification") or {}).get("level")
        if VERIFICATION_ORDER.get(level, 0) < VERIFICATION_ORDER[args.min_verification]:
            return False
    return True


def public_result(plugin, score=None):
    result = {key: plugin[key] for key in PUBLIC_FIELDS if plugin.get(key) not in (None, "", [])}
    if score is not None:
        result["lexicalScore"] = score
    return result


def normalize_repo(value):
    return (
        str(value or "")
        .casefold()
        .removeprefix("https://github.com/")
        .removeprefix("http://github.com/")
        .removeprefix("github.com/")
        .removesuffix(".git")
        .strip("/")
    )


def main():
    parser = argparse.ArgumentParser(
        description="Query the AllDSH DeepSeek Harness plugin catalog (alldsh.com only)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="Capability terms and synonyms prepared by the agent")
    mode.add_argument("--slug", help="Exact listing slug, e.g. modlens")
    mode.add_argument("--repo", help="Exact owner/repository, e.g. liustack/modlens")
    mode.add_argument(
        "--taxonomy",
        action="store_true",
        help="Print the catalog metadata: categories, use cases, verification scale and field contract",
    )
    parser.add_argument("--limit", type=int, default=20, help="Maximum candidates to return (1-50)")
    parser.add_argument("--category", help="Only listings in this category slug")
    parser.add_argument("--use-case", dest="use_case", help="Only listings in this use-case slug")
    parser.add_argument("--min-verification", choices=sorted(VERIFICATION_ORDER), help="Only listings verified at least this far")
    parser.add_argument("--security", choices=["scanned", "unverified", "flagged"], help="Only listings with this scan status")
    parser.add_argument("--health", choices=["active", "stable", "inactive", "archived"], help="Only listings with this health value")
    parser.add_argument("--json", action="store_true", help="Accepted for symmetry; output is always JSON")
    args = parser.parse_args()

    if not 1 <= args.limit <= 50:
        parser.error("--limit must be between 1 and 50")

    catalog = fetch_catalog()
    meta = catalog.get("meta") or {}

    if args.taxonomy:
        print(
            json.dumps(
                {
                    "catalog": CATALOG_URL,
                    "meta": meta,
                    "taxonomy": meta.get("taxonomy"),
                    "scales": meta.get("scales"),
                    "skills": meta.get("skills"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    plugins = [p for p in catalog["plugins"] if matches_filters(p, args)]

    if args.slug:
        matches = [p for p in plugins if str(p.get("slug") or "").casefold() == args.slug.casefold()]
        results = [public_result(p) for p in matches[:1]]
    elif args.repo:
        repository = normalize_repo(args.repo)
        matches = [p for p in plugins if normalize_repo(p.get("repo")) == repository]
        results = [public_result(p) for p in matches[:1]]
    else:
        ranked = [(score_plugin(p, args.query), p) for p in plugins]
        ranked = [(score, p) for score, p in ranked if score > 0]
        # Stars break ties only, so they never promote a weaker capability match.
        ranked.sort(key=lambda item: (item[0], int(item[1].get("stars") or 0)), reverse=True)
        results = [public_result(p, score) for score, p in ranked[: args.limit]]

    print(
        json.dumps(
            {
                "catalog": CATALOG_URL,
                "catalogVersion": meta.get("catalogVersion"),
                "lastUpdatedAt": meta.get("lastUpdatedAt"),
                "disclaimer": meta.get("disclaimer"),
                "docs": meta.get("docs"),
                "count": len(results),
                "matches": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        fail(str(error))
