"""Unit tests for inject_context.py."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inject_context import (  # noqa: E402
    parse_frontmatter,
    score_article,
    find_matches,
    render_paths,
    render_markdown,
)


# --- parse_frontmatter ---

def test_parse_frontmatter_basic():
    content = """---
title: Foo Bar
description: A test article
---

# Foo Bar

Body content here."""
    fm, body = parse_frontmatter(content)
    assert fm["title"] == "Foo Bar"
    assert fm["description"] == "A test article"
    assert body.startswith("# Foo Bar")


def test_parse_frontmatter_quoted_values():
    content = """---
title: "Foo Bar"
description: 'quoted'
---

body"""
    fm, _ = parse_frontmatter(content)
    assert fm["title"] == "Foo Bar"
    assert fm["description"] == "quoted"


def test_parse_frontmatter_no_frontmatter():
    content = "# Just markdown\n\nbody"
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_parse_frontmatter_unterminated():
    content = "---\ntitle: never closed\n\nstill in fm"
    fm, _ = parse_frontmatter(content)
    assert fm == {}  # graceful: treat as no frontmatter


# --- score_article ---

def test_score_title_match(tmp_path):
    art = tmp_path / "trading-verification.md"
    art.write_text("---\ntitle: x\n---\nirrelevant body")
    score, meta = score_article(art, ["trading"])
    assert score == 3  # title match only


def test_score_frontmatter_match(tmp_path):
    art = tmp_path / "foo.md"
    art.write_text("---\ndescription: about trading verify discipline\n---\nbody")
    score, _ = score_article(art, ["trading", "verify"])
    assert score == 4  # 2 fm * 2 words


def test_score_body_match(tmp_path):
    art = tmp_path / "foo.md"
    art.write_text("---\ntitle: x\n---\n\nThis article discusses trading verification.")
    score, _ = score_article(art, ["trading"])
    assert score == 1


def test_score_combined(tmp_path):
    art = tmp_path / "trading.md"
    art.write_text("---\ntitle: trading\ndescription: trading lens\n---\n\ntrading body")
    score, meta = score_article(art, ["trading"])
    # title +3, fm match (title field=trading + desc=trading lens) — both contain "trading"
    # all fm fields concatenated: "trading trading lens" → +2 (single hit per word)
    # body +1
    assert score == 6
    assert meta["title"] == "trading"


def test_score_zero_no_match(tmp_path):
    art = tmp_path / "foo.md"
    art.write_text("---\ntitle: foo\n---\n\nbody about cats")
    score, _ = score_article(art, ["dogs"])
    assert score == 0


def test_score_unreadable(tmp_path):
    art = tmp_path / "missing.md"
    score, meta = score_article(art, ["x"])
    assert score == 0
    assert meta == {}


# --- find_matches ---

def test_find_matches_skips_metadata(tmp_path):
    (tmp_path / "_index.md").write_text("trading trading trading")
    (tmp_path / "_log.md").write_text("trading")
    (tmp_path / "trading.md").write_text("---\ntitle: trading\n---\nbody")
    matches = find_matches(tmp_path, ["trading"], limit=10)
    names = [p.name for _, p, _ in matches]
    assert "trading.md" in names
    assert "_index.md" not in names
    assert "_log.md" not in names


def test_find_matches_sorted_by_score_desc(tmp_path):
    (tmp_path / "low-match.md").write_text("---\ntitle: x\n---\nbarely trading")
    (tmp_path / "high-match.md").write_text("---\ntitle: high-match\ndescription: trading\n---\ntrading body")
    matches = find_matches(tmp_path, ["trading"], limit=5)
    # low-match: body +1; high-match: fm +2 + body +1
    assert matches[0][1].name == "high-match.md"
    assert matches[0][0] > matches[1][0]


def test_find_matches_limit_caps(tmp_path):
    for i in range(10):
        (tmp_path / f"art-{i}.md").write_text(f"---\ntitle: a{i}\n---\nbody trading")
    matches = find_matches(tmp_path, ["trading"], limit=3)
    assert len(matches) == 3


def test_find_matches_empty_when_no_score(tmp_path):
    (tmp_path / "foo.md").write_text("body about cats")
    matches = find_matches(tmp_path, ["dogs"], limit=5)
    assert matches == []


# --- render functions ---

def test_render_paths(tmp_path):
    matches = [
        (5, tmp_path / "a.md", {}),
        (3, tmp_path / "b.md", {}),
    ]
    output = render_paths(matches)
    assert str(tmp_path / "a.md") in output
    assert str(tmp_path / "b.md") in output
    assert output.count("\n") == 1


def test_render_markdown(tmp_path):
    matches = [
        (5, tmp_path / "a.md", {"title": "A", "description": "About A"}),
    ]
    output = render_markdown(matches)
    assert "score=5" in output
    assert "title: A" in output
    assert "description: About A" in output
    assert "path:" in output


def test_render_markdown_handles_no_description(tmp_path):
    matches = [(3, tmp_path / "a.md", {"title": "A", "description": ""})]
    output = render_markdown(matches)
    assert "description:" not in output  # skip when empty
    assert "title: A" in output
