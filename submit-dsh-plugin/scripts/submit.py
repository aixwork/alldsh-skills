#!/usr/bin/env python3
"""File an AllDSH listing submission through the public intake API.

This is the final step of the submit-dsh-plugin skill: after the repository
has been checked against the review checklist and the listing material has
been produced, this script POSTs the submission to the AllDSH intake, which
re-checks the mechanical items and files a public review issue in
https://github.com/alldsh/submissions.

Standard library only. Exit codes:

    0  submission filed, or an open submission already exists (the issue URL
       is printed either way — add new information to that issue)
    1  the intake rejected the submission; the printed message says what to
       fix before retrying
    2  the intake could not be reached
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://www.alldsh.com/api/submit"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="File an AllDSH listing submission through the intake API.",
    )
    parser.add_argument("--repo", required=True, help='"owner/repo" or the github.com URL')
    parser.add_argument("--tagline", required=True, help="one sentence, at most 200 characters")
    parser.add_argument("--install", required=True, help="the exact install command for the listing")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        dest="categories",
        help="category slug from the catalog taxonomy; repeatable, at most 3",
    )
    parser.add_argument("--notes", help="credentials, paid endpoints, unusual permissions")
    parser.add_argument("--contact", help="how a reviewer can reach the maintainer")
    parser.add_argument("--listing-file", help="path to the listing-shaped markdown produced by the skill")
    parser.add_argument(
        "--kind",
        choices=["new", "correction"],
        default="new",
        help='"correction" when fixing an existing listing, "new" otherwise',
    )
    parser.add_argument(
        "--agent",
        default="submit-dsh-plugin skill",
        help="what is filing this submission (recorded in the issue footer)",
    )
    args = parser.parse_args()

    payload = {
        "repo": args.repo,
        "tagline": args.tagline,
        "install": args.install,
        "kind": args.kind,
        "agent": args.agent,
    }
    if args.categories:
        payload["categories"] = args.categories[:3]
    if args.notes:
        payload["notes"] = args.notes
    if args.contact:
        payload["contact"] = args.contact
    if args.listing_file:
        with open(args.listing_file, "r", encoding="utf-8") as handle:
            payload["listing"] = handle.read()

    endpoint = os.environ.get("ALLDSH_SUBMIT_URL", DEFAULT_ENDPOINT)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "submit-dsh-plugin"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            result = json.loads(error.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            result = {"error": "http_error", "message": f"The intake answered HTTP {error.code}."}
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Could not reach the intake at {endpoint}: {error}", file=sys.stderr)
        return 2

    if result.get("ok"):
        print(f"Submission filed: {result.get('issue')}")
        print(result.get("message", "Review happens publicly in that issue."))
        return 0

    error = result.get("error", "unknown")
    message = result.get("message", "")
    if error == "already_submitted":
        # Idempotent success: the queue already has this repository, so the
        # right move is a comment on the existing issue, not a second filing.
        print(f"Already submitted: {result.get('issue')}")
        print(message)
        return 0

    print(f"Not filed ({error}): {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
