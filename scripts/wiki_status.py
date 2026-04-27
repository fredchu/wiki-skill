#!/usr/bin/env python3
"""Show wiki statistics.

Usage:
    python3 wiki_status.py --wiki-dir <path>
"""

import argparse
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from absorb_log import get_pending, load_json
from rebuild_index import scan_articles, build_backlinks


def main():
    parser = argparse.ArgumentParser(description="Wiki status")
    parser.add_argument("--wiki-dir", required=True, help="Path to wiki directory")
    args = parser.parse_args()

    wiki_dir = args.wiki_dir

    articles = scan_articles(wiki_dir)
    backlinks = build_backlinks(articles)

    by_type: dict[str, int] = {}
    for a in articles:
        by_type[a["type"]] = by_type.get(a["type"], 0) + 1

    orphans = [a for a in articles if not backlinks.get(a["title"])]
    pending = get_pending(wiki_dir)

    absorb_log = load_json(os.path.join(wiki_dir, "_absorb_log.json"))
    if absorb_log:
        last_mtime = max(v["mtime"] for v in absorb_log.values())
        last_absorb = datetime.fromtimestamp(last_mtime).strftime("%Y-%m-%d %H:%M")
    else:
        last_absorb = "never"

    total_wikilinks = sum(len(a["wikilinks"]) for a in articles)
    total_backlinks = sum(len(v) for v in backlinks.values())

    print(f"Articles: {len(articles)}")
    for t, c in sorted(by_type.items()):
        print(f"  {t}: {c}")
    print(f"Last add: {last_absorb}")
    print(f"Pending source files: {len(pending)}")
    print(f"Orphan articles (0 backlinks): {len(orphans)}")
    for o in orphans:
        print(f"  {o['path']}")
    print(f"Total wikilinks: {total_wikilinks}")
    print(f"Total backlinks: {total_backlinks}")


if __name__ == "__main__":
    main()
