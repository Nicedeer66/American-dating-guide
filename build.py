#!/usr/bin/env python3
"""Build book.md -> PDF (WeasyPrint) and EPUB (pandoc)."""
import re, subprocess, pathlib, glob, sys
B = pathlib.Path(__file__).parent
TITLE = "美式恋爱指南"
SUB = "从美国年轻人的恋爱方式，系统学习恋爱、沟通与边界"
OUT = B / "dist"; OUT.mkdir(exist_ok=True)

def run(*a): subprocess.run(a, check=True)

# 0. generate Appendix A (English expressions index) from chapter tables
rows_out = ["# 附录 {.part .unnumbered}", "", "::: partdesc",
            "附录 A 英文表达索引 · 附录 B 求助资源汇总 · 附录 C 术语表", ":::", "",
            "# 附录 A　英文表达索引 {#appA}", "", "::: chapterlead",
            "按场景（章节）汇总全书“实用英文表达”表，方便复习与查找。", ":::", ""]
for f in sorted(glob.glob(str(B / "src" / "[01]*-ch*.md"))):
    t = pathlib.Path(f).read_text()
    m = re.search(r'^# (第 \d+ 章)　(.+?) \{', t, re.M)
    sec = re.search(r'## 五、实用英文表达\n\n(.*?)\n\n', t, re.S)
    if not (m and sec): continue
    lines = [l for l in sec.group(1).splitlines() if l.startswith('|')][2:]
    rows_out += [f"## {m.group(1)} · {m.group(2)}", "", "| 英文 | 中文意思 | 场景 |", "|---|---|---|"]
    for l in lines:
        c = [x.strip() for x in l.strip('|').split('|')]
        rows_out.append(f"| {c[0]} | {c[1]} | {c[2] if len(c) > 2 else ''} |")
    rows_out.append("")
(B / "src" / "20-appA.md").write_text("\n".join(rows_out))

# 1. assemble book.md
parts = sorted(glob.glob(str(B / "src" / "*.md")))
md = "\n\n".join(pathlib.Path(p).read_text() for p in parts)
# option lines (A. / （1）) inside one paragraph -> hard line breaks
md = re.sub(r'^((?:[A-D]\. |（\d+）).*)\n(?=(?:[A-D]\. |（\d+）))', r'\1\\\n', md, flags=re.M)
(OUT / "book.md").write_text(md)

# 2. HTML body for PDF
run("pandoc", str(OUT / "book.md"), "-f", "markdown-smart+fenced_divs+bracketed_spans",
    "-t", "html5", "--toc", "--toc-depth=1",
    "--template", str(B / "style" / "pdf.html"), "-o", str(OUT / "book.html"))
h = (OUT / "book.html").read_text()

# chapter number span:  "第 3 章　标题" -> <span class=chno>第 3 章</span>标题
h = re.sub(r'(<h1[^>]*>)(第 \d+ 章)　', r'\1<span class="chno">\2　</span>', h)
h = re.sub(r'(<h1[^>]*>)(专题|附录 [A-C])　', r'\1<span class="chno">\2　</span>', h)
# part pages: wrap h1.part + partdesc
h = re.sub(r'(<h1[^>]*class="[^"]*part[^"]*"[^>]*>.*?</h1>)\s*(<div class="partdesc">.*?</div>)',
           r'<section class="partpage">\1\2</section>', h, flags=re.S)
# TOC: mark part entries
part_ids = set([m.group(1) for t in re.findall(r'<h1[^>]*>', h) if 'part' in t for m in [re.search(r'id="([^"]+)"', t)] if m])
def tocfix(m):
    li = m.group(0)
    hid = re.search(r'href="#([^"]+)"', li)
    return li.replace("<li>", '<li class="toc-part">', 1) if hid and hid.group(1) in part_ids else li
h = re.sub(r'<li><a href="#[^"]+"[^>]*>.*?</a>', tocfix, h, flags=re.S)
# remove front-matter-only headings from TOC (copyright)
(OUT / "book.html").write_text(h)

from weasyprint import HTML, CSS
HTML(string=h, base_url=str(B)).write_pdf(str(OUT / f"{TITLE}.pdf"),
    stylesheets=[CSS(str(B / "style" / "pdf.css"))])
print("pdf ok")

# 3. cover PNG for EPUB from PDF page 1
import fitz
doc = fitz.open(OUT / f"{TITLE}.pdf")
pix = doc[0].get_pixmap(matrix=fitz.Matrix(1600 / doc[0].rect.width, 1600 / doc[0].rect.width))
pix.save(OUT / "cover.png"); print("cover", pix.width, pix.height)

# 4. EPUB
epub_md = re.sub(r'::: partdesc\n(.*?)\n:::', r'::: partdesc\n\1\n:::', md, flags=re.S)
(OUT / "book_epub.md").write_text(epub_md)
run("pandoc", str(OUT / "book_epub.md"), "-f", "markdown-smart+fenced_divs+bracketed_spans",
    "-t", "epub3", "--toc", "--toc-depth=1", "--split-level=1",
    "--css", str(B / "style" / "epub.css"),
    "--epub-cover-image", str(OUT / "cover.png"),
    "--metadata", "lang=zh-CN", "--metadata", "date=2026-10-16",
    "-o", str(OUT / f"{TITLE}.epub"))
print("epub ok")
