"""Helpers that build the project report in the BML Munjal University body format (python-docx).

Format measured from 'Body Format (3).docx.pdf' and 'Project-I File Front.docx.pdf' (A4, Times New Roman,
17 pt bold chapter titles, 12 pt body and sub-headings, justified text, ~24.5 pt line pitch, left margin ~3.5 cm).
"""
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor, Emu
from PIL import Image

FONT = "Times New Roman"
LINE_PT = 24.5          # measured line pitch of the template body text
AFTER_PT = 10


def _set_fonts(rpr, name=FONT):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(qn("w:" + a), name)


def style_font(style, size, bold=False, italic=False):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = RGBColor(0, 0, 0)
    _set_fonts(style.element.get_or_add_rPr())


class Report:
    def __init__(self):
        self.doc = Document()
        self.refs = {}          # key -> text
        self.order = []         # keys in order of first citation
        self.figs = []          # (number, description)
        self.tabs = []
        self.hnum = [0, 0, 0]
        self._setup()

    # ---------- setup ----------
    def _setup(self):
        d = self.doc
        s = d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin, s.right_margin = Cm(3.5), Cm(1.5)
        s.top_margin, s.bottom_margin = Cm(2.54), Cm(2.54)
        s.footer_distance = Cm(1.25)
        # document defaults
        rpr = d.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
        _set_fonts(rpr)
        st = d.styles
        n = st["Normal"]
        style_font(n, 12)
        pf = n.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # body text: the template's ~24.5 pt line pitch, justified
        bd = st.add_style("Body", 1)
        bd.base_style = n
        style_font(bd, 12)
        bd.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        bd.paragraph_format.line_spacing = Pt(LINE_PT)
        bd.paragraph_format.space_after = Pt(AFTER_PT)
        bd.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # headings
        h1 = st["Heading 1"]
        style_font(h1, 17, bold=True)
        h1.paragraph_format.page_break_before = True
        h1.paragraph_format.keep_with_next = True
        h1.paragraph_format.space_before = Pt(0)
        h1.paragraph_format.space_after = Pt(18)
        h1.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h2 = st["Heading 2"]
        style_font(h2, 12, bold=True)
        h2.paragraph_format.keep_with_next = True
        h2.paragraph_format.space_before = Pt(10)
        h2.paragraph_format.space_after = Pt(8)
        h2.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h2.paragraph_format.tab_stops.add_tab_stop(Cm(1.15))
        h2.paragraph_format.left_indent = Cm(1.15)
        h2.paragraph_format.first_line_indent = Cm(-1.15)
        h3 = st["Heading 3"]
        style_font(h3, 12, bold=True, italic=True)
        h3.paragraph_format.keep_with_next = True
        h3.paragraph_format.space_before = Pt(6)
        h3.paragraph_format.space_after = Pt(6)
        h3.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        h3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        h3.paragraph_format.tab_stops.add_tab_stop(Cm(1.6))
        h3.paragraph_format.left_indent = Cm(1.6)
        h3.paragraph_format.first_line_indent = Cm(-1.6)
        # front-matter heading (centred, not in the TOC)
        fh = st.add_style("Front Heading", 1)
        fh.base_style = st["Normal"]
        style_font(fh, 17, bold=True)
        fh.paragraph_format.page_break_before = True
        fh.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fh.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        fh.paragraph_format.space_after = Pt(18)
        # captions
        for nm in ("Figure Caption", "Table Caption"):
            c = st.add_style(nm, 1)
            c.base_style = st["Normal"]
            style_font(c, 11, bold=True)
            c.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            c.paragraph_format.space_before = Pt(4)
            c.paragraph_format.space_after = Pt(12)
        st["Table Caption"].paragraph_format.keep_with_next = True
        st["Table Caption"].paragraph_format.space_before = Pt(8)
        st["Table Caption"].paragraph_format.space_after = Pt(4)
        st["Figure Caption"].paragraph_format.keep_with_next = False
        tc = st.add_style("Table Text", 1)
        tc.base_style = st["Normal"]
        style_font(tc, 10)
        tc.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        tc.paragraph_format.space_after = Pt(2)
        tc.paragraph_format.space_before = Pt(2)
        tc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # bullets and references
        lb = st["List Bullet"]
        style_font(lb, 12)
        lb.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        lb.paragraph_format.line_spacing = Pt(LINE_PT)
        lb.paragraph_format.space_after = Pt(2)
        lb.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rf = st.add_style("Reference Item", 1)
        rf.base_style = st["Normal"]
        style_font(rf, 12)
        rf.paragraph_format.left_indent = Cm(0.9)
        rf.paragraph_format.first_line_indent = Cm(-0.9)
        rf.paragraph_format.space_after = Pt(6)
        rf.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        rf.paragraph_format.line_spacing = Pt(LINE_PT)
        rf.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for lvl, ind in ((1, 0.0), (2, 0.6)):
            t = st.add_style("toc %d" % lvl, 1)
            t.element.set(qn("w:styleId"), "TOC%d" % lvl)
            t.base_style = st["Normal"]
            style_font(t, 12, bold=(lvl == 1))
            t.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            t.paragraph_format.space_after = Pt(1)
            t.paragraph_format.left_indent = Cm(ind)
            t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            t.paragraph_format.tab_stops.add_tab_stop(Cm(16.0 - 0.0), alignment=2, leader=1)  # right, dots
        self._footer_for(d.sections[0], number=False)

    # ---------- sections and footer ----------
    def _footer_for(self, sec, number, fmt=None, start=None):
        sec.footer.is_linked_to_previous = False
        for p in list(sec.footer.paragraphs):
            for r in list(p._p):
                if r.tag != qn("w:pPr"):
                    p._p.remove(r)
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        if number:
            self._field(p, "PAGE")
        sp = sec._sectPr
        for e in sp.findall(qn("w:pgNumType")):
            sp.remove(e)
        if fmt or start is not None:
            pn = OxmlElement("w:pgNumType")
            if fmt:
                pn.set(qn("w:fmt"), fmt)
            if start is not None:
                pn.set(qn("w:start"), str(start))
            sp.append(pn)

    def new_section(self, number=True, fmt=None, start=None):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self._footer_for(sec, number, fmt, start)
        return sec

    def _field(self, p, instr, placeholder="1", bold=False):
        def r(t=None, fc=None, instrtext=None):
            run = p.add_run()
            run.font.name = FONT
            run.font.size = Pt(12)
            run.bold = bold
            if fc:
                e = OxmlElement("w:fldChar")
                e.set(qn("w:fldCharType"), fc)
                run._r.append(e)
            if instrtext:
                e = OxmlElement("w:instrText")
                e.set(qn("xml:space"), "preserve")
                e.text = instrtext
                run._r.append(e)
            if t:
                run.text = t
            return run
        r(fc="begin")
        r(instrtext=" %s " % instr)
        r(fc="separate")
        r(t=placeholder)
        r(fc="end")

    # ---------- inline markup ----------
    def _cite_sub(self, text):
        def rep(m):
            keys = m.group(1).split(",")
            nums = []
            for k in keys:
                k = k.strip()
                if k not in self.refs:
                    raise KeyError("unknown reference key " + k)
                if k not in self.order:
                    self.order.append(k)
                nums.append(self.order.index(k) + 1)
            return "[" + ", ".join(str(n) for n in sorted(nums)) + "]"
        return re.sub(r"\{([a-z0-9_,\s]+)\}", rep, text)

    def runs(self, p, text, size=None, bold=None):
        text = self._cite_sub(text)
        parts = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text)
        for part in parts:
            if not part:
                continue
            b = i = False
            if part.startswith("**") and part.endswith("**"):
                part, b = part[2:-2], True
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                part, i = part[1:-1], True
            r = p.add_run(part)
            if b or bold:
                r.bold = True
            if i:
                r.italic = True
            if size:
                r.font.size = Pt(size)
        return p

    # ---------- content blocks ----------
    def para(self, text, align=None, style=None):
        p = self.doc.add_paragraph(style=style or "Body")
        self.runs(p, text)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "left":
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        return p

    def bullets(self, items):
        for t in items:
            p = self.doc.add_paragraph(style="List Bullet")
            self.runs(p, t)

    def chapter(self, number, title):
        self.hnum = [number, 0, 0]
        self.doc.add_paragraph("%d. %s" % (number, title) if number else title, style="Heading 1")

    def h2(self, title):
        self.hnum[1] += 1
        self.hnum[2] = 0
        self.doc.add_paragraph("%d.%d\t%s" % (self.hnum[0], self.hnum[1], title), style="Heading 2")

    def h3(self, title):
        self.hnum[2] += 1
        self.doc.add_paragraph("%d.%d.%d\t%s" % (self.hnum[0], self.hnum[1], self.hnum[2], title), style="Heading 3")

    def table(self, header, rows, widths_cm, caption, align_num=True, font=10, bold_first_col=False):
        n = len([t for t in self.tabs if t[0].startswith("Table %d." % self.hnum[0])]) + 1
        label = "Table %d.%d" % (self.hnum[0], n)
        self.tabs.append((label, caption))
        cp = self.doc.add_paragraph(style="Table Caption")
        self.runs(cp, "%s  %s" % (label, caption))
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)

        def fill(cell, text, bold=False, shade=None, center=False):
            p = cell.paragraphs[0]
            p.style = self.doc.styles["Table Text"]
            self.runs(p, text, size=font, bold=bold)
            if center:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if shade:
                tcPr = cell._tc.get_or_add_tcPr()
                sh = OxmlElement("w:shd")
                sh.set(qn("w:val"), "clear")
                sh.set(qn("w:color"), "auto")
                sh.set(qn("w:fill"), shade)
                tcPr.append(sh)

        for j, h in enumerate(header):
            c = t.rows[0].cells[j]
            fill(c, h, bold=True, shade="D9D9D9", center=True)
            c.width = Cm(widths_cm[j])
        # repeat header row
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
        for row in rows:
            cells = t.add_row().cells
            for j, v in enumerate(row):
                isnum = align_num and j > 0 and re.fullmatch(r"[\d.,/%\s*()+\-–<>≥≤±x]+", str(v) or "") is not None
                fill(cells[j], str(v), bold=(bold_first_col and j == 0), center=isnum)
                cells[j].width = Cm(widths_cm[j])
        for r in t.rows:
            trPr = r._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            cs.set(qn("w:val"), "true")
            trPr.append(cs)
        if len(rows) <= 9:
            for r_ in t.rows[:-1]:
                for c_ in r_.cells:
                    for p_ in c_.paragraphs:
                        p_.paragraph_format.keep_with_next = True
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(6)
        sp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        return t

    def figure(self, path, caption, width_cm=15.5):
        n = len([f for f in self.figs if f[0].startswith("Figure %d." % self.hnum[0])]) + 1
        label = "Figure %d.%d" % (self.hnum[0], n)
        self.figs.append((label, caption))
        paths = path if isinstance(path, (list, tuple)) else [path]
        wc = min(width_cm, 15.5)
        for k, pth in enumerate(paths):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(4)
            p.add_run().add_picture(pth, width=Cm(wc))
        cp = self.doc.add_paragraph(style="Figure Caption")
        self.runs(cp, "%s  %s" % (label, caption))

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def toc(self):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        self._field(p, 'TOC \\o "1-2" \\h \\z \\u', placeholder="Right-click and choose Update Field to build the table of contents.")

    def reference_list(self):
        for i, k in enumerate(self.order, 1):
            p = self.doc.add_paragraph(style="Reference Item")
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
            self.runs(p, "[%d]\t%s" % (i, self.refs[k]))

    def save(self, path):
        self.doc.save(path)
