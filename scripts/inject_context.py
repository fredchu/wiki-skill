#!/usr/bin/env python3
"""Inject relevant wiki article paths into a fork prompt by topic match.

Usage:
    inject_context.py "<topic>" [--limit N] [--format paths|markdown] [--wiki-dir DIR]

Output:
    paths (default) — one absolute path per line, ready to paste into a fork prompt.
    markdown        — title + description + score per article, for main-session preview.

Scoring:
    title (filename) match : +3
    frontmatter (desc/sources/related) match : +2
    body first 500 chars match : +1
    score=0 articles excluded.

Source: 2026-04-29 dual-axis token-maxing audit, 🟡 改善 #8 (fork prompt 自動
inject wiki context — 半自動 reflex 版).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_WIKI_DIR = Path("/Users/fredchu/Documents/For_Claude/wiki")
SCORE_TITLE = 3
SCORE_FRONTMATTER = 2
SCORE_BODY = 1
BODY_PREVIEW_CHARS = 500


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-ish frontmatter at file start. Return (fields, rest).

    Lightweight — only handles `key: value` lines (no nested arrays / objects).
    Quoted-string values get their surrounding quotes stripped.
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 4)
    if end == -1:
        return {}, content
    fm_block = content[4:end]
    rest = content[end + 4:].lstrip("\n")
    fields: dict = {}
    for line in fm_block.splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip().strip('"').strip("'")
    return fields, rest


def score_article(path: Path, topic_words: list[str]) -> tuple[int, dict]:
    """Score an article by where the topic words appear.

    Returns (score, metadata). metadata = {"title", "description"}.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0, {}

    title_from_filename = path.stem.replace("-", " ").lower()
    fm, body = parse_frontmatter(content)

    score = 0
    for w in topic_words:
        if w in title_from_filename:
            score += SCORE_TITLE

    fm_text = " ".join(str(v) for v in fm.values()).lower()
    for w in topic_words:
        if w in fm_text:
            score += SCORE_FRONTMATTER

    body_preview = body[:BODY_PREVIEW_CHARS].lower()
    for w in topic_words:
        if w in body_preview:
            score += SCORE_BODY

    return score, {
        "title": fm.get("title", path.stem.replace("-", " ").title()),
        "description": fm.get("description", ""),
    }


def find_matches(wiki_dir: Path, topic_words: list[str], limit: int) -> list[tuple[int, Path, dict]]:
    """Scan wiki dir and return top-N (score, path, meta) by score desc."""
    candidates: list[tuple[int, Path, dict]] = []
    for art in sorted(wiki_dir.glob("*.md")):
        # Skip metadata files (_index.md / _log.md / etc.)
        if art.name.startswith("_"):
            continue
        score, meta = score_article(art, topic_words)
        if score > 0:
            candidates.append((score, art, meta))
    candidates.sort(key=lambda x: (-x[0], x[1].name))
    return candidates[:limit]


def render_paths(matches: list[tuple[int, Path, dict]]) -> str:
    return "\n".join(str(art) for _, art, _ in matches)


def render_markdown(matches: list[tuple[int, Path, dict]]) -> str:
    lines: list[str] = []
    for score, art, meta in matches:
        lines.append(f"## {art.name} (score={score})")
        lines.append(f"path: {art}")
        if meta.get("title"):
            lines.append(f"title: {meta['title']}")
        desc = meta.get("description", "")
        if desc:
            lines.append(f"description: {desc[:200]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> int:
    p = argparse.ArgumentParser(description="Find relevant wiki articles by topic match")
    p.add_argument("topic", help="topic keyword(s), space-separated")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--format", choices=["paths", "markdown"], default="paths")
    p.add_argument("--wiki-dir", default=str(DEFAULT_WIKI_DIR))
    args = p.parse_args()

    # `[\w-]+` keeps kebab-case tokens together (e.g. "session-handoff" stays one
    # word) to avoid generic single-word matches like "session" from over-matching.
    topic_words = [w.lower() for w in re.findall(r"[\w-]+", args.topic) if len(w) >= 2]
    if not topic_words:
        print("ERROR: no topic words (need at least one word ≥ 2 chars)", file=sys.stderr)
        return 1

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.is_dir():
        print(f"ERROR: wiki dir not found: {wiki_dir}", file=sys.stderr)
        return 2

    matches = find_matches(wiki_dir, topic_words, args.limit)
    if not matches:
        print(f"WARN: no wiki article matches topic {args.topic!r}", file=sys.stderr)
        return 1

    if args.format == "paths":
        print(render_paths(matches))
    else:
        print(render_markdown(matches))
    return 0


if __name__ == "__main__":
    sys.exit(main())
