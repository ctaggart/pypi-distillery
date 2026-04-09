#!/usr/bin/env python3
"""Check for new distillery releases and signal when a new tag should be created."""

# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import logging
import os
import sys

import requests  # type: ignore[import-untyped]

UPSTREAM_REPO = "ekristen/distillery"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def github_headers() -> dict[str, str]:
    """Build headers for GitHub API requests."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_release_tag() -> str:
    """Fetch the latest release tag name from upstream."""
    url = f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest"
    resp = requests.get(url, headers=github_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()["tag_name"]


def tag_exists(repo: str, tag: str) -> bool:
    """Check if a git tag already exists in our repository."""
    url = f"https://api.github.com/repos/{repo}/git/ref/tags/{tag}"
    resp = requests.get(url, headers=github_headers(), timeout=30)
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    resp.raise_for_status()
    return False


def set_github_output(name: str, value: str) -> None:
    """Write a key=value pair to $GITHUB_OUTPUT for use in subsequent workflow steps."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        log.info("GITHUB_OUTPUT not set (running locally?); would set %s=%s", name, value)


def main() -> None:
    our_repo = os.environ.get("GITHUB_REPOSITORY", "ctaggart/pypi-distillery")
    log.info("Checking for new %s releases...", UPSTREAM_REPO)

    tag_name = get_latest_release_tag()

    if not tag_name.startswith("v"):
        log.error("Unexpected tag format: %s", tag_name)
        sys.exit(1)

    log.info("Latest upstream release: %s", tag_name)

    if tag_exists(our_repo, tag_name):
        log.info("Tag %s already exists in %s — nothing to do", tag_name, our_repo)
        set_github_output("new_version", "")
        return

    log.info("New release %s is ready for tagging", tag_name)
    set_github_output("new_version", tag_name)


if __name__ == "__main__":
    main()
