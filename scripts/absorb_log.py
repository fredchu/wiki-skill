#!/usr/bin/env python3
"""Scan source directories and report files needing absorption.

Usage:
    python3 absorb_log.py --wiki-dir <path>                    # report pending files
    python3 absorb_log.py --wiki-dir <path> --mark <file_path> --articles art1.md,art2.md  # mark as absorbed
    python3 absorb_log.py --wiki-dir <path> --source <file>    # check single file
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def scan_sources(sources_json: dict) -> list[dict]:
    """Return list of {path, type, mtime} for all source files."""
    files = []
    exclude = set(sources_json.get("exclude", []))

    for src in sources_json["source_dirs"]:
        base = Path(src["path"])
        if not base.exists():
            print(f"WARNING: source dir not found: {base}", file=sys.stderr)
            continue

        globs = src["glob"] if isinstance(src["glob"], list) else [src["glob"]]
        for g in globs:
            if "**" in g:
                matches = base.rglob(g.replace("**/", ""))
            else:
                matches = base.glob(g)

            for match in matches:
                if match.name in exclude:
                    continue
                if match.is_file():
                    files.append({
                        "path": str(match),
                        "type": src["type"],
                        "mtime": match.stat().st_mtime,
                    })
    return files


def get_pending(wiki_dir: str, source_path: str | None = None) -> list[dict]:
    """Return files that are new or modified since last absorption."""
    sources_json = load_json(os.path.join(wiki_dir, "_sources.json"))
    absorb_log = load_json(os.path.join(wiki_dir, "_absorb_log.json"))

    all_files = scan_sources(sources_json)

    if source_path:
        source_path = os.path.abspath(source_path)
        all_files = [f for f in all_files if f["path"] == source_path]

    pending = []
    for f in all_files:
        key = f["path"]
        if key not in absorb_log:
            f["reason"] = "new"
            pending.append(f)
        elif f["mtime"] > absorb_log[key]["mtime"]:
            f["reason"] = "modified"
            pending.append(f)

    return sorted(pending, key=lambda x: x["mtime"])


def mark_absorbed(wiki_dir: str, file_path: str, articles: list[str]) -> None:
    """Mark a file as absorbed into the given wiki articles."""
    log_path = os.path.join(wiki_dir, "_absorb_log.json")
    absorb_log = load_json(log_path)

    file_path = os.path.abspath(file_path)
    absorb_log[file_path] = {
        "mtime": os.path.getmtime(file_path),
        "absorbed_into": articles,
    }
    save_json(log_path, absorb_log)


def main():
    parser = argparse.ArgumentParser(description="Wiki absorb log manager")
    parser.add_argument("--wiki-dir", required=True, help="Path to wiki directory")
    parser.add_argument("--mark", help="Mark a file as absorbed")
    parser.add_argument("--articles", help="Comma-separated list of wiki articles (used with --mark)")
    parser.add_argument("--source", help="Check single source file only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.mark:
        articles = args.articles.split(",") if args.articles else []
        mark_absorbed(args.wiki_dir, args.mark, articles)
        print(f"Marked as absorbed: {args.mark} → {articles}")
        return

    pending = get_pending(args.wiki_dir, args.source)

    if args.json:
        json.dump(pending, sys.stdout, indent=2, ensure_ascii=False)
    else:
        if not pending:
            print("No pending files. Wiki is up to date.")
            return
        print(f"{len(pending)} file(s) pending absorption:\n")
        for f in pending:
            print(f"  [{f['reason']:8s}] [{f['type']:10s}] {f['path']}")


if __name__ == "__main__":
    main()
