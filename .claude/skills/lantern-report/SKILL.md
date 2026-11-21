---
name: lantern-report
description: Rebuild or edit the BML Munjal University project report (report/ folder). Use when asked to update, fill in, re-render or check the report docx or pdf.
---

# LANTERN project report

Files in `report/`: `content.py` (all text and tables), `refs.py` (reference list), `docbuild.py` (format helpers), `build_report.py` (build), `word_update.ps1` (Word updates the contents field and exports the PDF). Outputs: `LANTERN_Project_Report.docx` and `.pdf`.

## Rebuild
```bash
cd report && PYTHONIOENCODING=utf-8 python build_report.py
```
Needs Microsoft Word installed (it opens the file hidden), python-docx, pymupdf and Pillow. It takes about 2 minutes: it builds, lets Word update the table of contents, reads figure and table pages from the PDF, rebuilds, and exports again. Delete `report/build/` and `__pycache__` afterwards.

## Format (measured from the college PDFs, not guessed)
A4; Times New Roman; chapter titles 17 pt bold; sub-headings 12 pt bold numbered like 2.1; body 12 pt justified at about 24.5 pt line pitch; left margin about 3.5 cm. Chapter order follows the template list: title, declarations, acknowledgement, contents, abstract, lists of figures, tables and abbreviations, then Introduction, Literature Review, Problem Statement, Methodology, Results, Conclusions, References, Plagiarism Check Report (under 10%).

## Rules
- Numbers come from `out/**` result files or the docs they cite. Do not copy sample text from the college format file (it is about an unrelated topic).
- Fill identity fields from the user only. Still blank until given: Neil's and Khushi's contribution lines, mentor designation, supervisor signature, plagiarism report page.
- References use `{key}` markers in `content.py`; numbers are assigned in order of first citation.
- After a rebuild, render pages with pymupdf (`page.get_pixmap(dpi=72)`) and look at them; check tables do not overflow and the contents page is right.
- Do not invent a plagiarism report or claim one exists.
