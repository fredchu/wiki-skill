#!/usr/bin/env python3
"""Append entries to wiki _log.md.

Usage:
    python3 wiki_log.py --wiki-dir <path> --op ingest --detail "absorbed foo.md → bar, baz"
    python3 wiki_log.py --wiki-dir <path> --op query --detail "ASR技術整體認知"
    python3 wiki_log.py --wiki-dir <path> --op lint --detail "2 broken links fixed, 89 em dashes removed"
"""

import argparse
import os
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Append to wiki log")
    parser.add_argument("--wiki-dir", required=True)
    parser.add_argument("--op", required=True, choices=["ingest", "query", "lint", "search", "status"])
    parser.add_argument("--detail", required=True)
    args = parser.parse_args()

    log_path = os.path.join(args.wiki_dir, "_log.md")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"## [{now}] {args.op} | {args.detail}\n\n"

    if not os.path.exists(log_path):
        header = "# Wiki Log\n\nAppend-only timeline of wiki operations.\n\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(header + entry)
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    print(f"Logged: [{now}] {args.op} | {args.detail}")


if __name__ == "__main__":
    main()
