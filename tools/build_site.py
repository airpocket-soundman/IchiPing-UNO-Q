"""Build the GitHub Pages HTML from the Markdown documents (single source).

usage: python tools/build_site.py
Each Markdown file listed in PAGES is converted to the HTML file next to it
(or to the given output), using docs/style.css.  Only the Markdown subset used
in this repository is supported: ATX headings, paragraphs, bold/italic/code
spans, links, images, fenced code blocks, block quotes, bullet/numbered lists
and pipe tables.  Keeping the conversion here (no third-party dependency)
means the .md and .html pairs can never drift apart.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# markdown source -> (html output, page title, language)
PAGES = {
    "README.md": ("index.html", "UNO Ping", "en"),
    "docs/uno_q/hardware.md": ("docs/uno_q/hardware.html", "Hardware and wiring", "en"),
    "docs/uno_q/software.md": ("docs/uno_q/software.html", "Software architecture", "en"),
    "docs/uno_q/signal_and_model.md": ("docs/uno_q/signal_and_model.html", "Acoustic sensing and model", "en"),
    "docs/uno_q/data_and_training.md": ("docs/uno_q/data_and_training.html", "Data collection and training", "en"),
    "docs/uno_q/results.md": ("docs/uno_q/results.html", "Results", "en"),
    "docs/uno_q/reproduce.md": ("docs/uno_q/reproduce.html", "Reproduce UNO Ping", "en"),
    "pc/runs/model_comparison_20260912.md": ("pc/runs/model_comparison_20260912.html", "Model comparison", "en"),
    "docs/hackster/story_en.md": ("docs/hackster/story_en.html", "Hackster story (English)", "en"),
    "docs/hackster/story_ja.md": ("docs/hackster/story_ja.html", "Hackster 記事（日本語版）", "ja"),
}

NAV = [
    ("index.html", "Home"),
    ("docs/uno_q/hardware.html", "Hardware"),
    ("docs/uno_q/software.html", "Software"),
    ("docs/uno_q/signal_and_model.html", "Signal & model"),
    ("docs/uno_q/data_and_training.html", "Data & training"),
    ("docs/uno_q/results.html", "Results"),
    ("docs/uno_q/reproduce.html", "Reproduce"),
    ("docs/hackster/story_en.html", "Hackster story"),
]


def inline(text: str) -> str:
    """Escape and apply inline Markdown (code, images, links, bold, italic)."""
    parts = re.split(r"(`[^`]+`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        s = html.escape(part, quote=False)
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                   lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy">', s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                   lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
        s = re.sub(r"(?<![\"'=(])\b(https?://[^\s<)]+)", r'<a href="\1">\1</a>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        out.append(s)
    return "".join(out)


def table(lines: list[str]) -> str:
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    head, body = rows[0], rows[2:]
    th = "".join(f"<th>{inline(c)}</th>" for c in head)
    tb = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(block))}</code></pre>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            anchor = re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")
            out.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            out.append(table(block))
            continue
        if line.startswith(">"):
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(lines[i][1:].strip())
                i += 1
            out.append(f"<blockquote>{convert(chr(10).join(block))}</blockquote>")
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.", line))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or
                                      (lines[i].startswith("   ") and items)):
                if re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(t)}</li>" for t in items) + f"</{tag}>")
            continue
        if not line.strip():
            i += 1
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|```|>|\s*([-*]|\d+\.)\s|\s*\||---$)", lines[i]):
            para.append(lines[i])
            i += 1
        text = " ".join(p.strip() for p in para)
        if text.startswith("[IMAGE") or text.startswith("[VIDEO") or text.startswith("[PHOTO"):
            out.append(f'<p class="placeholder">{inline(text)}</p>')
        else:
            out.append(f"<p>{inline(text)}</p>")
    return "\n".join(out)


def rel(target: str, page: str) -> str:
    depth = len(Path(page).parent.parts)
    return ("../" * depth) + target


def build(src: str, dst: str, title: str, lang: str) -> None:
    md = (REPO / src).read_text(encoding="utf-8")
    md = re.sub(r"\]\(([^)\s]+)\.md(#[^)]*)?\)", lambda m: f"]({m.group(1)}.html{m.group(2) or ''})", md)
    body = convert(md)
    links = []
    for href, label in NAV:
        current = ' class="current"' if href == dst else ""
        links.append(f'<a href="{rel(href, dst)}"{current}>{html.escape(label)}</a>')
    nav = "".join(links)
    page = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{rel('docs/site.css', dst)}">
</head>
<body>
<header class="site-header"><a class="brand" href="{rel('index.html', dst)}">UNO Ping</a><nav>{nav}</nav></header>
<main class="content">
{body}
</main>
<footer class="site-footer">Generated from <code>{html.escape(src)}</code> by <code>tools/build_site.py</code> — edit the Markdown, not this file.</footer>
</body>
</html>
"""
    (REPO / dst).parent.mkdir(parents=True, exist_ok=True)
    (REPO / dst).write_text(page, encoding="utf-8")
    print(f"{src} -> {dst}")


def main() -> None:
    for src, (dst, title, lang) in PAGES.items():
        if (REPO / src).is_file():
            build(src, dst, title, lang)
        else:
            print(f"skip (missing): {src}")


if __name__ == "__main__":
    main()
