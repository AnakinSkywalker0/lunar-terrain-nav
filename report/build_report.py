"""Build the LANTERN project report.

Passes: (0) build to collect figure/table labels; (1) build with placeholder page numbers and let Word update the TOC and
export a PDF; (2) read caption pages from the PDF, rebuild with real page numbers and let Word update again.
Usage: python build_report.py   (needs Microsoft Word for the TOC field and the PDF export)
"""
import os
import re
import subprocess
import sys

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docbuild import Report  # noqa: E402
import content  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FINAL = os.path.join(HERE, "LANTERN_Project_Report.docx")
os.makedirs(BUILD, exist_ok=True)


def make(path, figs, tabs, pages):
    r = Report()
    from refs import REFS
    r.refs = dict(REFS)
    content.front(r, figs, tabs, pages)
    content.body(r)
    r.save(path)
    return r


def word(src, dst_docx, dst_pdf):
    ps = os.path.join(HERE, "word_update.ps1")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps, src, dst_docx, dst_pdf], check=True)


def caption_pages(pdf):
    doc = pymupdf.open(pdf)
    texts = [p.get_text() for p in doc]
    start = None
    for i, t in enumerate(texts):
        if t.strip().splitlines()[0].strip() == "1":
            start = i
            break
    if start is None:
        raise RuntimeError("chapter 1 page not found")
    return doc, texts, start


def collect(pdf, figs, tabs):
    doc, texts, start = caption_pages(pdf)
    pages = {}
    for lab, cap in figs + tabs:
        key = (lab + "  " + cap)[:40]
        found = None
        for i in range(start, len(texts)):
            flat = re.sub(r"\s+", " ", texts[i])
            if re.sub(r"\s+", " ", key) in flat:
                found = i - start + 1
                break
        pages[lab] = str(found) if found else "0"
    return pages


if __name__ == "__main__":
    r0 = make(os.path.join(BUILD, "pass0.docx"), [], [], {})
    figs, tabs = list(r0.figs), list(r0.tabs)
    print("figures", len(figs), "tables", len(tabs), "refs cited", len(r0.order), "of", len(r0.refs))
    make(os.path.join(BUILD, "pass1.docx"), figs, tabs, {})
    word(os.path.join(BUILD, "pass1.docx"), os.path.join(BUILD, "pass1_w.docx"), os.path.join(BUILD, "pass1.pdf"))
    pages = collect(os.path.join(BUILD, "pass1.pdf"), figs, tabs)
    missing = [k for k, v in pages.items() if v == "0"]
    print("pages found", len(pages) - len(missing), "missing", missing)
    make(os.path.join(BUILD, "pass2.docx"), figs, tabs, pages)
    word(os.path.join(BUILD, "pass2.docx"), FINAL, os.path.join(HERE, "LANTERN_Project_Report.pdf"))
    print("done")
