#!/usr/bin/env python3
"""Rebuild _index.md and _backlinks.json from wiki articles.

Usage:
    python3 rebuild_index.py --wiki-dir <path>
    python3 rebuild_index.py --wiki-dir <path> --dry-run
"""

import argparse
import json
import os
import re
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter as a dict (simple parser, no PyYAML dependency)."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in content[3:end].strip().split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("-"):
            key, _, value = line.partition(":")
            value = value.strip().strip('"').strip("'")
            if value and not value.startswith("["):
                fm[key.strip()] = value
    return fm


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilink]] targets from content."""
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def scan_articles(wiki_dir: str) -> list[dict]:
    """Scan all .md articles in wiki_dir (excluding _ prefixed files and _outputs/)."""
    articles = []
    wiki_path = Path(wiki_dir)

    for md_file in wiki_path.rglob("*.md"):
        rel = md_file.relative_to(wiki_path)
        if rel.parts[0].startswith("_") or rel.name.startswith("_"):
            continue

        content = md_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(content)
        wikilinks = extract_wikilinks(content)

        articles.append({
            "path": str(rel),
            "title": fm.get("title", rel.stem),
            "type": fm.get("type", "unknown"),
            "created": fm.get("created", ""),
            "last_updated": fm.get("last_updated", ""),
            "wikilinks": wikilinks,
            "line_count": len(content.split("\n")),
        })

    return sorted(articles, key=lambda a: a["path"])


def build_backlinks(articles: list[dict]) -> dict:
    """Build reverse link index: {title: [articles that link to it]}.

    Resolves wikilink targets to canonical article titles by matching
    against both the title and the filename stem (slug).
    """
    # Build lookup maps: slug -> title, lower(title) -> title
    slug_to_title: dict[str, str] = {}
    title_lower_to_title: dict[str, str] = {}
    for a in articles:
        stem = Path(a["path"]).stem
        slug_to_title[stem] = a["title"]
        title_lower_to_title[a["title"].lower()] = a["title"]

    def resolve_link(link: str) -> str:
        """Resolve a wikilink target to canonical title."""
        # Exact title match
        if link in title_lower_to_title.values():
            return link
        # Slug match (e.g., "agent-teams" -> "Agent Teams")
        if link in slug_to_title:
            return slug_to_title[link]
        # Case-insensitive title match
        if link.lower() in title_lower_to_title:
            return title_lower_to_title[link.lower()]
        # No match — return as-is (may be a future article)
        return link

    backlinks: dict[str, list[dict]] = {}
    for a in articles:
        for link in a["wikilinks"]:
            resolved = resolve_link(link)
            if resolved not in backlinks:
                backlinks[resolved] = []
            backlinks[resolved].append({
                "from_title": a["title"],
                "from_path": a["path"],
            })
    return backlinks


def generate_index_md(articles: list[dict], backlinks: dict) -> str:
    """Generate _index.md content."""
    lines = ["# Wiki Index", ""]
    lines.append(f"Total: {len(articles)} articles")
    lines.append("")

    by_type: dict[str, list[dict]] = {}
    for a in articles:
        t = a["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(a)

    for article_type in sorted(by_type.keys()):
        type_articles = by_type[article_type]
        lines.append(f"## {article_type} ({len(type_articles)})")
        lines.append("")
        for a in sorted(type_articles, key=lambda x: x["title"]):
            bl_count = len(backlinks.get(a["title"], []))
            lines.append(f"- [[{a['title']}]] — `{a['path']}` ({a['line_count']} lines, {bl_count} backlinks)")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Rebuild wiki index and backlinks")
    parser.add_argument("--wiki-dir", required=True, help="Path to wiki directory")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing files")
    args = parser.parse_args()

    articles = scan_articles(args.wiki_dir)
    backlinks = build_backlinks(articles)

    if args.dry_run:
        print(f"Articles: {len(articles)}")
        types: dict[str, int] = {}
        for a in articles:
            types[a["type"]] = types.get(a["type"], 0) + 1
        for t, c in sorted(types.items()):
            print(f"  {t}: {c}")
        print(f"Total wikilinks: {sum(len(a['wikilinks']) for a in articles)}")
        print(f"Total backlink targets: {len(backlinks)}")
        orphans = [a for a in articles if not backlinks.get(a["title"])]
        print(f"Orphan articles (0 backlinks): {len(orphans)}")
        return

    index_content = generate_index_md(articles, backlinks)
    index_path = os.path.join(args.wiki_dir, "_index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    print(f"Wrote {index_path} ({len(articles)} articles)")

    backlinks_path = os.path.join(args.wiki_dir, "_backlinks.json")
    with open(backlinks_path, "w", encoding="utf-8") as f:
        json.dump(backlinks, f, indent=2, ensure_ascii=False)
    print(f"Wrote {backlinks_path} ({len(backlinks)} targets)")


if __name__ == "__main__":
    main()
