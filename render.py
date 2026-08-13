"""Render WRITEUP.md to a single self-contained HTML file with figures inlined."""
import base64
import html
import os
import re
import sys

ROOT = os.path.expanduser("~/asic-puzzle-2026")
OUT = sys.argv[1] if len(sys.argv) > 1 else "preview.html"
SRC = sys.argv[2] if len(sys.argv) > 2 else "WRITEUP.md"


def inline_figure(path, width=None):
    full = os.path.join(ROOT, path)
    if path.endswith(".svg"):
        svg = open(full).read()
        svg = re.sub(r'^<\?xml[^>]*\?>\s*', '', svg)
        svg = re.sub(r'<svg([^>]*?)\swidth="[^"]*"\sheight="[^"]*"', r'<svg\1', svg, count=1)
        svg = svg.replace('<svg ', '<svg class="fig" ', 1)
        if width:
            return ('<span class="figbox" style="width:%spx">%s</span>' % (width, svg))
        return svg
    data = base64.b64encode(open(full, "rb").read()).decode()
    ext = "gif" if path.endswith(".gif") else "png"
    w = ' style="width:%spx"' % width if width else ""
    return '<img class="fig" %s src="data:image/%s;base64,%s" alt="">' % (w, ext, data)


def inline_html_figures(block):
    def sub(m):
        attrs = m.group(0)
        src = re.search(r'src="([^"]+)"', attrs).group(1)
        w = re.search(r'width="(\d+)"', attrs)
        if not src.startswith("figures/"):
            return attrs
        return inline_figure(src, w.group(1) if w else None)
    return re.sub(r'<img\s[^>]*>', sub, block)


def spans(t):
    t = html.escape(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    return t


def render(md):
    out = []
    # Pull fenced blocks out before splitting on blank lines: a code block may
    # contain one, and splitting first tears it in half.
    fences = []

    def stash(m):
        fences.append(m.group(0))
        return "\n\n\x00FENCE%d\x00\n\n" % (len(fences) - 1)

    md = re.sub(r'(?ms)^```.*?^```', stash, md)
    blocks = re.split(r'\n\s*\n', md)
    blocks = [fences[int(b.strip()[6:-1])] if b.strip().startswith("\x00FENCE") else b
              for b in blocks]
    for b in blocks:
        b = b.strip("\n")
        if not b.strip():
            continue
        if b.startswith("```"):
            body = b.split("\n", 1)[1].rsplit("```", 1)[0]
            out.append("<pre><code>%s</code></pre>" % html.escape(body.rstrip("\n")))
        elif b.startswith("<p align="):
            out.append('<figure>%s</figure>' % inline_html_figures(b))
        elif b.strip() in ('<div align="center">', "</div>"):
            out.append(b.strip())
        elif b.startswith("!["):
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', b)
            out.append('<figure>%s</figure>' % inline_figure(m.group(2)))
        elif b.startswith("# "):
            out.append("<h1>%s</h1>" % spans(b[2:]))
        elif b.startswith("## "):
            out.append("<h2>%s</h2>" % spans(b[3:]))
        elif b.lstrip().startswith("|"):
            rows = [r for r in b.split("\n") if r.strip().startswith("|")]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            align = []
            if len(cells) > 1 and all(set(c) <= set("-: ") for c in cells[1]):
                align = ["right" if c.endswith(":") else "left" for c in cells[1]]
                cells.pop(1)
            t = ["<table><thead><tr>"]
            t += ["<th>%s</th>" % spans(c) for c in cells[0]]
            t.append("</tr></thead><tbody>")
            for row in cells[1:]:
                t.append("<tr>")
                for i, c in enumerate(row):
                    a = align[i] if i < len(align) else "left"
                    t.append('<td style="text-align:%s">%s</td>' % (a, spans(c)))
                t.append("</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
        elif b.lstrip().startswith("- "):
            items = re.split(r'\n(?=- )', b)
            t = ["<ul>"]
            for it in items:
                t.append("<li>%s</li>" % spans(" ".join(it.strip()[2:].split())))
            t.append("</ul>")
            out.append("".join(t))
        elif b.startswith("*") and b.rstrip().endswith("*") and not b.startswith("**"):
            out.append('<p class="caption">%s</p>' % spans(" ".join(b.strip("*\n").split())))
        else:
            out.append("<p>%s</p>" % spans(" ".join(b.split())))
    return "\n".join(out)


CSS = """
:root { --ink:#12151a; --dim:#767f90; --line:#ccd2dd; --surf:#fbfcfd; --accent:#2a78d6; }
* { box-sizing: border-box; }
body { margin:0; background:var(--surf); color:var(--ink);
  font:16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif; }
main { max-width: 46rem; margin: 0 auto; padding: 4rem 1.5rem 6rem; }
h1 { font-size: 2rem; line-height:1.2; margin:0 0 1.5rem; letter-spacing:-.02em; }
h2 { font-size: 1.25rem; margin:3rem 0 1rem; letter-spacing:-.01em; }
p { margin: 0 0 1.1rem; }
a { color: var(--accent); }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
code { font-size: .88em; background:#eef1f5; padding:.1em .3em; border-radius:3px; }
pre { background:#fff; border:1px solid var(--line); border-radius:6px;
  padding: .9rem 1rem; overflow-x:auto; font-size:12px; line-height:1.5; }
pre code { background:none; padding:0; font-size:inherit; }
figure { margin: 2rem 0 2rem; text-align:center; }
figure p { margin:0; }
figure br { line-height: 2.4; }
.figbox { display:inline-block; max-width:100%; }
.fig { display:block; margin:0 auto; max-width:100%; height:auto;
  border:1px solid var(--line); border-radius:6px; background:#fff; }
.caption { color: var(--ink); font-size:.88rem; margin:.6rem 0 2rem; }
div[align=center] { text-align:center; }
div[align=center] table { margin-left:auto; margin-right:auto; text-align:left; }
table { border-collapse:collapse; margin:0 auto 1.5rem; font-size:.92rem;
  display:table; width:fit-content; max-width:100%; }
th, td { border-bottom:1px solid var(--line); padding:.5rem .6rem; text-align:left; }
th { color:var(--ink); font-weight:600; font-size:.82rem; text-transform:uppercase;
  letter-spacing:.04em; }
ul { margin:0 0 1.1rem; padding-left:1.2rem; }
li { margin-bottom:.5rem; }
"""

md = open(os.path.join(ROOT, SRC)).read()
title = md.split("\n", 1)[0].lstrip("# ").strip()
page = ("<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>%s</title><style>%s</style></head><body><main>%s</main></body></html>"
        % (html.escape(title), CSS, render(md)))
open(OUT, "w").write(page)
print("wrote %s (%.0f KB)" % (OUT, os.path.getsize(OUT) / 1024))
