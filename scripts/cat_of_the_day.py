#!/usr/bin/env python3
"""Swap the secret Eva page background for a fresh cat photo.

Pulls a batch of candidates from an open cat API, keeps the highest-resolution
one (a background wants pixels), saves it into assets/images/backgrounds/, and
rewrites the background rule in css/secret.css with a dated cache-buster.

Stdlib only, so it runs anywhere Python 3 does -- no pip install in CI.

Usage:
    python3 scripts/cat_of_the_day.py                  # update files only
    python3 scripts/cat_of_the_day.py --commit         # ...and commit
    python3 scripts/cat_of_the_day.py --commit --push  # ...and push to origin
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_FILE = os.path.join(REPO, "css", "secret.css")
BACKGROUNDS = os.path.join(REPO, "assets", "images", "backgrounds")
LOG_FILE = os.path.join(REPO, "CAT_LOG.md")
IMAGE_STEM = "cat-of-the-day"

USER_AGENT = "EthanTilakWebsite-cat-of-the-day/1.0 (+https://github.com/tilake280/EthanTilakWebsite)"
CANDIDATE_COUNT = 10
MIN_BYTES = 20_000  # anything smaller is a thumbnail or an error page

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def fetch(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "").split(";")[0].strip()


def from_the_cat_api():
    """TheCatAPI returns width/height, so we can pick the biggest of a batch."""
    url = (
        "https://api.thecatapi.com/v1/images/search"
        f"?limit={CANDIDATE_COUNT}&mime_types=jpg,png&size=full&order=RANDOM"
    )
    key = os.environ.get("CAT_API_KEY")
    if key:
        url += f"&api_key={key}"

    payload, _ = fetch(url)
    candidates = [c for c in json.loads(payload) if c.get("url")]
    if not candidates:
        raise RuntimeError("TheCatAPI returned no usable candidates")

    best = max(candidates, key=lambda c: (c.get("width") or 0) * (c.get("height") or 0))
    return best["url"], f"TheCatAPI ({best.get('width')}x{best.get('height')})"


def from_cataas():
    """Fallback: Cataas (https://github.com/Freyja-moth/cataas), no size metadata."""
    payload, _ = fetch("https://cataas.com/cat?json=true")
    cat_id = json.loads(payload).get("_id") or json.loads(payload).get("id")
    if not cat_id:
        raise RuntimeError("Cataas returned no cat id")
    return f"https://cataas.com/cat/{cat_id}", "Cataas"


def pick_cat():
    errors = []
    for source in (from_the_cat_api, from_cataas):
        try:
            url, credit = source()
            data, content_type = fetch(url)
            if content_type not in EXTENSIONS:
                raise RuntimeError(f"unexpected content type {content_type!r} from {url}")
            if len(data) < MIN_BYTES:
                raise RuntimeError(f"image from {url} is only {len(data)} bytes")
            return data, EXTENSIONS[content_type], url, credit
        except (urllib.error.URLError, json.JSONDecodeError, RuntimeError, OSError) as exc:
            errors.append(f"{source.__name__}: {exc}")
    raise SystemExit("Could not fetch a cat.\n  " + "\n  ".join(errors))


def save_image(data, extension):
    """Write the new background and clear out any previous day's extension."""
    os.makedirs(BACKGROUNDS, exist_ok=True)
    for stale in os.listdir(BACKGROUNDS):
        if stale.startswith(IMAGE_STEM + ".") and not stale.endswith(extension):
            os.remove(os.path.join(BACKGROUNDS, stale))

    filename = IMAGE_STEM + extension
    with open(os.path.join(BACKGROUNDS, filename), "wb") as handle:
        handle.write(data)
    return filename


def update_css(filename, today):
    """Point the body background at the new file, cache-busted by date."""
    with open(CSS_FILE, encoding="utf-8") as handle:
        css = handle.read()

    replacement = f"background: url(../assets/images/backgrounds/{filename}?v={today});"
    css, count = re.subn(r"background:\s*url\([^)]*\);", replacement, css, count=1)
    if count != 1:
        raise SystemExit(f"Could not find the background rule in {CSS_FILE}")

    with open(CSS_FILE, "w", encoding="utf-8") as handle:
        handle.write(css)


def append_log(today, source_url, credit):
    header = "# Cat of the Day\n\nA log of every cat that has served as the secret Eva page background.\n\n"
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as handle:
            handle.write(header)
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(f"- {today} - [{credit}]({source_url})\n")


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], check=True, capture_output=True, text=True)


def commit(today, push):
    paths = ["css/secret.css", "assets/images/backgrounds", "CAT_LOG.md"]
    git("add", "--all", "--", *paths)
    if not git("status", "--porcelain", "--", *paths).stdout.strip():
        print("Nothing changed, skipping commit.")
        return
    git("commit", "-m", f"Cat of the day: {today}")
    print(f"Committed cat of the day for {today}.")
    if push:
        git("push")
        print("Pushed to origin.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true", help="commit the updated files")
    parser.add_argument("--push", action="store_true", help="push the commit to origin")
    args = parser.parse_args()

    today = datetime.date.today().isoformat()
    data, extension, source_url, credit = pick_cat()
    filename = save_image(data, extension)
    update_css(filename, today)
    append_log(today, source_url, credit)
    print(f"{today}: {filename} ({len(data) // 1024} KB) from {credit} -> {source_url}")

    if args.commit:
        try:
            commit(today, args.push)
        except subprocess.CalledProcessError as exc:
            sys.exit(f"git failed: {exc.stderr.strip() or exc}")


if __name__ == "__main__":
    main()
