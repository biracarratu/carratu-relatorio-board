#!/usr/bin/env python3
"""Gerador de relatórios Carratu (DOCX e PDF), comum às skills do Carratu Growth Kit.

Uso:
  python3 carratu_report.py report.json --out outputs [--auto auto_sections.json ...]
         [--format full|onepager|both] [--brand assets/brand.json] [--onepager-brand ...] [--no-pdf]

- report.json: narrativa escrita pelo Claude (formato em references/report-schema.md de cada skill).
- --auto: blocos calculados pelos scripts da skill (números, tabelas, gráficos). Entram antes das
  seções escritas pelo Claude, para que todo número do relatório venha de cálculo e não de memória.
- Idioma: campo "lang" do report.json ("pt" ou "en"). Os rótulos fixos do relatório seguem o idioma.

Report writer for the Carratu Growth Kit skills. Same usage in English; set "lang": "en".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor, Cm
except ImportError:
    raise SystemExit("Instale python-docx / install python-docx: pip install python-docx --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "assets"))

L = {
    "pt": {
        "prepared_for": "Preparado para", "date": "Data", "by": "Por", "summary": "Resumo executivo",
        "priorities": "3 prioridades", "strength": "Maior força", "context": "Contexto",
        "sources": "Fontes de dados", "recs": "Recomendações priorizadas", "plan": "Plano 30 · 60 · 90 dias",
        "days": "dias", "limits": "Limitações e confiança", "method": "Metodologia",
        "prio": "Prioridade", "action": "Ação", "effort": "Esforço", "impact": "Impacto", "owner": "Dono",
        "confidence": "Confiança", "score": "Nota", "kpis": "Indicadores-chave", "appendix": "Anexo",
        "toc_note": "Todos os números deste relatório foram calculados pelos scripts da skill a partir dos dados "
                    "fornecidos. Interpretação e recomendações: Claude, com a metodologia Carratu.",
        "pass": "OK", "warn": "Atenção", "fail": "Crítico", "na": "N/A", "unknown": "Não avaliado",
        "field": "Campo", "value": "Valor", "next": "Próximo passo",
    },
    "en": {
        "prepared_for": "Prepared for", "date": "Date", "by": "By", "summary": "Executive summary",
        "priorities": "Top 3 priorities", "strength": "Biggest strength", "context": "Context",
        "sources": "Data sources", "recs": "Prioritized recommendations", "plan": "30 · 60 · 90 day plan",
        "days": "days", "limits": "Limitations and confidence", "method": "Methodology",
        "prio": "Priority", "action": "Action", "effort": "Effort", "impact": "Impact", "owner": "Owner",
        "confidence": "Confidence", "score": "Score", "kpis": "Key metrics", "appendix": "Appendix",
        "toc_note": "Every number in this report was computed by the skill scripts from the data provided. "
                    "Interpretation and recommendations: Claude, using the Carratu methodology.",
        "pass": "OK", "warn": "Watch", "fail": "Critical", "na": "N/A", "unknown": "Not assessed",
        "field": "Field", "value": "Value", "next": "Next step",
    },
}
PRIO_KEY = {"critica": "critical", "critical": "critical", "alta": "high", "high": "high", "media": "medium",
            "medium": "medium", "ganho rapido": "quickwin", "quick win": "quickwin", "quickwin": "quickwin",
            "baixa": "medium", "low": "medium"}
CTX_LABELS = {"pt": {"business": "Negócio", "icp": "ICP", "market": "Mercado", "goal": "Objetivo",
                     "competitors": "Concorrentes", "period": "Período", "target": "Meta"},
              "en": {"business": "Business", "icp": "ICP", "market": "Market", "goal": "Goal",
                     "competitors": "Competitors", "period": "Period", "target": "Target"}}


def norm(txt):
    return "".join(ch for ch in unicodedata.normalize("NFD", str(txt).lower().strip())
                   if unicodedata.category(ch) != "Mn")


# ------------------------------------------------------------------ docx helpers
def rgb(h):
    return RGBColor.from_string(str(h).upper())


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:shd")):
        tcPr.remove(old)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for k, v in (("top", top), ("bottom", bottom), ("start", left), ("end", right)):
        el = OxmlElement(f"w:{k}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def table_borders(table, color="E5E7EB", size=4, inside=True):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        el = OxmlElement(f"w:{e}")
        if inside or e in ("top", "left", "bottom", "right"):
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:color"), color)
        else:
            el.set(qn("w:val"), "nil")
        b.append(el)
    tblPr.append(b)


def set_col_widths(table, widths_cm):
    table.autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr
    for old in tblPr.findall(qn("w:tblW")) + tblPr.findall(qn("w:tblLayout")):
        tblPr.remove(old)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tw.set(qn("w:type"), "dxa")
    tblPr.append(tw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    cols = tbl.tblGrid.findall(qn("w:gridCol"))
    for i, w in enumerate(widths_cm):
        if i < len(cols):
            cols[i].set(qn("w:w"), str(int(w * 567)))
    for row in table.rows:
        for i, w in enumerate(widths_cm):
            if i < len(row.cells):
                row.cells[i].width = Cm(w)


def repeat_header(row):
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    row._tr.get_or_add_trPr().append(el)


def keep_row_together(row):
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    row._tr.get_or_add_trPr().append(el)


def add_field(paragraph, instr):
    run = paragraph.add_run()
    for t in ("begin", "instr", "separate", "end"):
        if t == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = instr
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), t)
        run._r.append(el)
    return run


def para_border_bottom(p, color, size=8):
    pPr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    el = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", str(size)), ("space", "4"), ("color", color)):
        el.set(qn(f"w:{k}"), v)
    bdr.append(el)
    pPr.append(bdr)


def set_page_background(doc, hex_color):
    body = doc.element
    for old in body.findall(qn("w:background")):
        body.remove(old)
    bg = OxmlElement("w:background")
    bg.set(qn("w:color"), hex_color)
    body.insert(0, bg)
    settings = doc.settings.element
    if settings.find(qn("w:displayBackgroundShape")) is None:
        settings.insert(0, OxmlElement("w:displayBackgroundShape"))


def letter_spacing(run, twips):
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:val"), str(twips))
    run._r.get_or_add_rPr().append(sp)


def asset_path(brand, rel):
    if not rel:
        return None
    p = rel if os.path.isabs(rel) else os.path.join(brand.get("_dir", ASSETS), rel)
    return p if os.path.exists(p) else None


# ------------------------------------------------------------------ writer
class Writer:
    def __init__(self, brand, lang="pt"):
        self.b = brand
        self.c = brand["colors"]
        self.t = L.get(lang, L["pt"])
        self.lang = lang if lang in L else "pt"
        self.dark = brand.get("theme") == "dark"
        self.doc = Document()
        st = self.doc.styles["Normal"]
        font = brand.get("font", "Arial")
        st.font.name = font
        st.element.rPr.rFonts.set(qn("w:eastAsia"), font)
        st.font.size = Pt(10.5)
        st.font.color.rgb = rgb(self.c["text"])
        st.paragraph_format.space_after = Pt(6)
        st.paragraph_format.line_spacing = 1.15
        hfont = brand.get("heading_font") or font
        for lvl, size in ((1, 20), (2, 14), (3, 12)):
            h = self.doc.styles[f"Heading {lvl}"]
            h.font.name = hfont
            h.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
            h.element.rPr.rFonts.set(qn("w:hAnsiTheme"), "")
            h.font.size = Pt(size)
            h.font.bold = True
            if self.dark:
                h.font.color.rgb = rgb(self.c["text"] if lvl != 2 else self.c.get("eyebrow", self.c["primary"]))
            else:
                h.font.color.rgb = rgb(self.c["dark"] if lvl != 2 else self.c["primary"])
            h.paragraph_format.space_before = Pt(18 if lvl == 1 else 12)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2)
        sec.top_margin = sec.bottom_margin = Cm(2)
        self.width = 17.0
        if self.dark:
            set_page_background(self.doc, self.c["page_bg"])

    def status_color(self, key):
        return {"pass": self.c["pass"], "warn": self.c["warn"], "fail": self.c["fail"],
                "critical": self.c["critical"], "high": self.c["high"], "medium": self.c["medium"],
                "quickwin": self.c["quickwin"]}.get(key, self.c["na"])

    def score_color(self, s):
        if s is None:
            return self.c["na"]
        return self.c["pass"] if s >= 75 else self.c["warn"] if s >= 50 else self.c["fail"]

    def runs(self, para, text, size=None, bold=False, color=None, italic=False):
        for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", str(text))):
            if not part:
                continue
            r = para.add_run(part)
            r.bold = bold or (i % 2 == 1)
            r.italic = italic
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = rgb(color)
        return para

    def p(self, text="", size=None, bold=False, color=None, italic=False, align=None, after=None, before=None):
        para = self.doc.add_paragraph()
        if text:
            self.runs(para, text, size=size, bold=bold, color=color, italic=italic)
        if align == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if after is not None:
            para.paragraph_format.space_after = Pt(after)
        if before is not None:
            para.paragraph_format.space_before = Pt(before)
        return para

    def paragraphs(self, text):
        for chunk in [x for x in str(text or "").split("\n\n") if x.strip()]:
            self.p(chunk.strip())

    def bullet(self, text):
        para = self.doc.add_paragraph(style="List Bullet")
        self.runs(para, text)
        para.paragraph_format.space_after = Pt(3)

    def numbered(self, text):
        para = self.doc.add_paragraph(style="List Number")
        self.runs(para, text)
        para.paragraph_format.space_after = Pt(3)

    def cell_text(self, cell, text, bold=False, color=None, size=9.5, align=None, italic=False):
        cell.text = ""
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)
        self.runs(para, "" if text is None else text, size=size, bold=bold, color=color, italic=italic)
        if align == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        return para

    def table(self, header, rows, widths=None, status_col=None, zebra=True, size=9.5):
        n = len(header)
        widths = widths or [self.width / n] * n
        if abs(sum(widths) - self.width) > 0.05:
            k = self.width / sum(widths)
            widths = [w * k for w in widths]
        t = self.doc.add_table(rows=1, cols=n)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_borders(t, self.c["border"])
        hdr = t.rows[0]
        repeat_header(hdr)
        hdr_fill = self.c.get("deep", self.c["dark"]) if self.dark else self.c["dark"]
        for i, h in enumerate(header):
            c = hdr.cells[i]
            shade(c, hdr_fill)
            cell_margins(c)
            self.cell_text(c, h, bold=True, color="FFFFFF", size=9)
        for ri, row in enumerate(rows):
            r = t.add_row()
            keep_row_together(r)
            for i in range(n):
                val = row[i] if i < len(row) else ""
                c = r.cells[i]
                cell_margins(c)
                if status_col is not None and i == status_col:
                    custom = None
                    if "|" in str(val):  # "rótulo|pass" mostra o rótulo com a cor do status
                        custom, val = str(val).split("|", 1)
                    key = norm(val)
                    key = PRIO_KEY.get(key, key)
                    label = custom or (self.t.get(key, val) if key in ("pass", "warn", "fail", "na", "unknown") else val)
                    shade(c, self.status_color(key))
                    self.cell_text(c, label, bold=True, color="FFFFFF", size=8.5, align="center")
                else:
                    if zebra and ri % 2 == 1:
                        shade(c, self.c["light_bg"])
                    self.cell_text(c, val, size=size)
        set_col_widths(t, widths)
        self.p(after=4)
        return t

    def callout(self, text, title=None, fill=None, border=None):
        t = self.doc.add_table(rows=1, cols=1)
        table_borders(t, border or self.c["primary"], size=12, inside=False)
        c = t.rows[0].cells[0]
        shade(c, fill or self.c.get("panel", self.c["light_bg"]))
        cell_margins(c, 160, 160, 200, 200)
        c.text = ""
        para = c.paragraphs[0]
        if title:
            self.runs(para, title, bold=True, size=11, color=self.c["primary"])
            para = c.add_paragraph()
        for i, chunk in enumerate([x for x in str(text).split("\n\n") if x.strip()]):
            if i:
                para = c.add_paragraph()
            self.runs(para, chunk.strip(), size=10.5)
        set_col_widths(t, [self.width])
        self.p(after=6)

    def kpi_tiles(self, items, per_row=4):
        items = list(items or [])
        if not items:
            return
        for start in range(0, len(items), per_row):
            chunk = items[start:start + per_row]
            t = self.doc.add_table(rows=1, cols=len(chunk))
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            table_borders(t, self.c["border"], size=4)
            keep_row_together(t.rows[0])
            for i, k in enumerate(chunk):
                c = t.rows[0].cells[i]
                fill = self.c["panel"] if self.dark else self.c["light_bg"]
                shade(c, fill)
                cell_margins(c, 140, 140, 120, 120)
                c.text = ""
                para = c.paragraphs[0]
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_after = Pt(0)
                st = norm(k.get("status", ""))
                color = self.status_color(st) if st in ("pass", "warn", "fail") else (
                    self.c["primary"] if not self.dark else self.c.get("primary_soft", self.c["primary"]))
                para.paragraph_format.keep_with_next = True
                self.runs(para, str(k.get("value", "")), size=16 if len(str(k.get("value", ""))) <= 9 else 13, bold=True, color=color)
                p2 = c.add_paragraph()
                p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p2.paragraph_format.space_after = Pt(0)
                self.runs(p2, k.get("label", ""), size=8.5, bold=True, color=self.c["text"])
                if k.get("note"):
                    p3 = c.add_paragraph()
                    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p3.paragraph_format.space_after = Pt(0)
                    self.runs(p3, k["note"], size=7.5, color=self.c["muted"])
            set_col_widths(t, [self.width / len(chunk)] * len(chunk))
            self.p(after=4)

    def score_bars(self, items):
        """Notas 0-100 por pilar como barra horizontal em tabela (sem depender de imagem)."""
        rows = []
        t = self.doc.add_table(rows=0, cols=3)
        table_borders(t, self.c["border"], size=2, inside=False)
        for it in items:
            r = t.add_row()
            keep_row_together(r)
            s = it.get("score")
            self.cell_text(r.cells[0], it.get("name", ""), bold=True, size=9.5)
            bar = r.cells[1]
            bar.text = ""
            para = bar.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            blocks = int(round((s or 0) / 5))
            rr = para.add_run("█" * blocks)
            rr.font.color.rgb = rgb(self.score_color(s))
            rr.font.size = Pt(9)
            rr2 = para.add_run("█" * (20 - blocks))
            rr2.font.color.rgb = rgb(self.c["border"])
            rr2.font.size = Pt(9)
            self.cell_text(r.cells[2], f"{s if s is not None else '-'}" + (f"  · {it['note']}" if it.get("note") else ""),
                           size=9, color=self.c["text"])
            for c in r.cells:
                cell_margins(c, 60, 60, 100, 100)
        set_col_widths(t, [4.5, 6.0, 6.5])
        self.p(after=4)

    def image(self, path, width_cm=None, caption=None):
        if not path or not os.path.exists(path):
            self.p(f"[{os.path.basename(str(path))}]", italic=True, color=self.c["muted"], size=9)
            return
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(path, width=Cm(min(width_cm or self.width, self.width)))
        if caption:
            self.p(caption, size=8.5, italic=True, color=self.c["muted"], align="center", after=8)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def header_footer(self, left, right):
        sec = self.doc.sections[0]
        hp = sec.header.paragraphs[0]
        hp.text = ""
        self.runs(hp, left, size=8.5, bold=True, color=self.c["text"] if self.dark else self.c["dark"])
        hp.add_run("\t\t")
        self.runs(hp, right, size=8.5, color=self.c["muted"])
        para_border_bottom(hp, self.c["primary"], 8)
        fp = sec.footer.paragraphs[0]
        fp.text = ""
        pf = self.b.get("producer_footer")
        self.runs(fp, self.b.get("footer_credit", ""), size=8, color=self.c["muted"])
        fp.add_run("\t\t")
        r = add_field(fp, "PAGE")
        r.font.size = Pt(8)
        if pf:
            fp2 = sec.footer.add_paragraph()
            fp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.runs(fp2, pf.get("text", "") + "  ", size=7, color=self.c["muted"])
            logo = asset_path(self.b, pf.get("logo"))
            if logo:
                fp2.add_run().add_picture(logo, width=Cm(min(int(pf.get("max_width_px", 70)), 70) * 2.54 / 96))

    # ---------------------------------------------------------- blocks
    def block(self, b, base_dir):
        typ = b.get("type")
        if b.get("title"):
            self.doc.add_heading(b["title"], level=3)
        if typ == "text":
            self.paragraphs(b.get("text"))
        elif typ == "bullets":
            for it in b.get("items", []):
                self.bullet(it)
        elif typ == "numbered":
            for it in b.get("items", []):
                self.numbered(it)
        elif typ == "table":
            self.table(b["header"], b.get("rows", []), b.get("widths"), b.get("status_col"), size=b.get("size", 9.5))
        elif typ == "kpis":
            self.kpi_tiles(b.get("items"), b.get("per_row", 4))
        elif typ == "scores":
            self.score_bars(b.get("items", []))
        elif typ == "chart" or typ == "image":
            path = b.get("path")
            if path and not os.path.isabs(path):
                cand = os.path.join(base_dir, path)
                path = cand if os.path.exists(cand) else path
            self.image(path, b.get("width_cm"), b.get("caption"))
        elif typ == "callout":
            self.callout(b.get("text", ""), b.get("callout_title") or b.get("heading"))
        elif typ == "page_break":
            self.page_break()
        if b.get("note"):
            self.p(b["note"], size=8.5, italic=True, color=self.c["muted"])

    def sections(self, sections, base_dir):
        for s in sections or []:
            h = self.doc.add_heading(s.get("title", ""), level=2 if s.get("level", 2) == 2 else 1)
            if s.get("page_break_before"):
                h.paragraph_format.page_break_before = True
            if s.get("intro"):
                self.paragraphs(s["intro"])
            for b in s.get("blocks", []):
                self.block(b, base_dir)


# ------------------------------------------------------------------ documents
def cover(W, rep):
    c = W.c
    t = W.t
    logo = asset_path(W.b, W.b.get("logo_on_light") if not W.dark else W.b.get("logo"))
    if logo:
        para = W.doc.add_paragraph()
        para.add_run().add_picture(logo, width=Cm(W.b.get("logo_width_cm", 4.2)))
    eyebrow = W.p(rep.get("eyebrow") or W.b.get("methodology_name", ""), size=9, bold=True,
                  color=c.get("eyebrow", c["primary"]), before=36, after=4)
    for r in eyebrow.runs:
        letter_spacing(r, 20)
    W.p(rep.get("title", ""), size=28, bold=True, color=c["text"] if W.dark else c["dark"], after=4)
    if rep.get("subtitle"):
        W.p(rep["subtitle"], size=13, color=c["muted"], after=18)
    meta = []
    if rep.get("client_name"):
        meta.append(f"**{t['prepared_for']}:** {rep['client_name']}")
    if rep.get("date"):
        meta.append(f"**{t['date']}:** {rep['date']}")
    meta.append(f"**{t['by']}:** {W.b.get('author', '')} · {W.b.get('agency', '')}")
    for m in meta:
        W.p(m, size=10.5, after=2)
    W.p(after=12)
    sc = rep.get("score")
    if sc:
        tt = W.doc.add_table(rows=1, cols=2)
        table_borders(tt, c["border"], size=4, inside=False)
        a, b = tt.rows[0].cells
        shade(a, W.score_color(sc.get("value")))
        cell_margins(a, 200, 200, 200, 200)
        a.text = ""
        pa = a.paragraphs[0]
        pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
        W.runs(pa, f"{sc.get('value', '-')}", size=40, bold=True, color="FFFFFF")
        pb = a.add_paragraph()
        pb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        W.runs(pb, "/100", size=10, color="FFFFFF")
        shade(b, c["panel"] if W.dark else c["light_bg"])
        cell_margins(b, 200, 200, 240, 200)
        b.text = ""
        W.runs(b.paragraphs[0], sc.get("label", t["score"]), size=14, bold=True)
        if sc.get("confidence") is not None:
            W.runs(b.add_paragraph(), f"{t['confidence']}: {sc['confidence']}%", size=9.5, color=c["muted"])
        if sc.get("verdict"):
            W.runs(b.add_paragraph(), sc["verdict"], size=10.5)
        set_col_widths(tt, [4.5, W.width - 4.5])
        W.p(after=8)
    if rep.get("kpis"):
        W.kpi_tiles(rep["kpis"][:8])


def build_full(rep, autos, brand, out_docx, base_dir):
    W = Writer(brand, rep.get("lang", "pt"))
    t = W.t
    W.header_footer(rep.get("client_name") or brand.get("agency", ""), rep.get("title", ""))
    cover(W, rep)
    W.page_break()

    W.doc.add_heading(t["summary"], level=1)
    W.paragraphs(rep.get("executive_summary"))
    if rep.get("top_priorities"):
        W.doc.add_heading(t["priorities"], level=2)
        for pr in rep["top_priorities"][:3]:
            W.numbered(pr)
    if rep.get("biggest_strength"):
        W.callout(rep["biggest_strength"], title=t["strength"])
    if rep.get("context"):
        W.doc.add_heading(t["context"], level=2)
        rows = []
        for k, v in rep["context"].items():
            label = CTX_LABELS[W.lang].get(k, k.replace("_", " ").capitalize())
            rows.append([label, ", ".join(v) if isinstance(v, list) else str(v)])
        W.table([t["field"], t["value"]], rows, [4.5, 12.5])
    if rep.get("data_sources"):
        W.doc.add_heading(t["sources"], level=2)
        for s in rep["data_sources"]:
            W.bullet(s)
        W.p(t["toc_note"], size=8.5, italic=True, color=W.c["muted"])
    secs = rep.get("sections") or []
    W.sections([s for s in secs if s.get("position") != "end"], base_dir)
    for auto in autos:
        W.sections(auto.get("sections"), auto.get("_dir", base_dir))
    W.sections([s for s in secs if s.get("position") == "end"], base_dir)

    if rep.get("recommendations"):
        h = W.doc.add_heading(t["recs"], level=1)
        h.paragraph_format.page_break_before = True
        order = {"critical": 0, "high": 1, "quickwin": 2, "medium": 3}
        recs = sorted(rep["recommendations"], key=lambda r: order.get(PRIO_KEY.get(norm(r.get("priority", "")), "medium"), 9))
        rows = []
        for r in recs:
            action = f"**{r.get('issue', '')}**" + (f"\n{r['how']}" if r.get("how") else "")
            rows.append([r.get("priority", ""), action, r.get("effort", ""), r.get("impact", ""), r.get("owner", "")])
        W.table([t["prio"], t["action"], t["effort"], t["impact"], t["owner"]], rows,
                [2.6, 8.8, 1.8, 1.8, 2.0], status_col=0, zebra=True, size=9)
    ap = rep.get("action_plan")
    if ap:
        W.doc.add_heading(t["plan"], level=2)
        for k in ("30", "60", "90"):
            if ap.get(k):
                W.doc.add_heading(f"{k} {t['days']}", level=3)
                for it in ap[k]:
                    W.bullet(it)
    if rep.get("limitations"):
        W.doc.add_heading(t["limits"], level=2)
        for it in rep["limitations"]:
            W.bullet(it)
    if rep.get("methodology"):
        W.doc.add_heading(t["method"], level=2)
        W.paragraphs(rep["methodology"])
    if brand.get("cta_title"):
        W.p(after=6)
        W.callout(rep.get("cta_text") or brand.get("cta_text", ""), title=rep.get("cta_title") or brand["cta_title"])
        W.p(brand.get("cta_url", ""), bold=True, color=W.c["primary"], align="center")
    W.doc.save(out_docx)
    return out_docx


def build_onepager(rep, brand, out_docx):
    W = Writer(brand, rep.get("lang", "pt"))
    c = W.c
    t = W.t
    sec = W.doc.sections[0]
    sec.top_margin = sec.bottom_margin = Cm(1.4)
    pf = brand.get("producer_footer")
    if pf:
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        W.runs(fp, pf.get("text", "") + "  ", size=7, color=c["muted"])
        logo = asset_path(brand, pf.get("logo"))
        if logo:
            fp.add_run().add_picture(logo, width=Cm(min(int(pf.get("max_width_px", 70)), 70) * 2.54 / 96))
    logo = asset_path(brand, brand.get("logo") if W.dark else brand.get("logo_on_light"))
    if logo:
        W.doc.add_paragraph().add_run().add_picture(logo, width=Cm(brand.get("logo_width_cm", 4.2)))
    e = W.p((rep.get("eyebrow") or "").upper(), size=8.5, bold=True, color=c.get("eyebrow", c["primary"]), before=10, after=2)
    for r in e.runs:
        letter_spacing(r, 30)
    W.p(rep.get("onepager_title") or rep.get("title", ""), size=22, bold=True, color=c["text"], after=2)
    W.p(" · ".join(x for x in [rep.get("client_name"), rep.get("date")] if x), size=9.5, color=c["muted"], after=10)
    sc = rep.get("score")
    if sc:
        tt = W.doc.add_table(rows=1, cols=2)
        table_borders(tt, c["border"], size=4, inside=False)
        a, b = tt.rows[0].cells
        shade(a, W.score_color(sc.get("value")))
        cell_margins(a, 160, 160, 160, 160)
        a.text = ""
        pa = a.paragraphs[0]
        pa.alignment = WD_ALIGN_PARAGRAPH.CENTER
        W.runs(pa, f"{sc.get('value', '-')}", size=32, bold=True, color="FFFFFF")
        shade(b, c.get("panel", c["light_bg"]))
        cell_margins(b, 160, 160, 200, 160)
        b.text = ""
        W.runs(b.paragraphs[0], sc.get("label", t["score"]), size=12, bold=True)
        if sc.get("verdict"):
            W.runs(b.add_paragraph(), sc["verdict"], size=10)
        set_col_widths(tt, [3.6, W.width - 3.6])
        W.p(after=6)
    if rep.get("kpis"):
        W.kpi_tiles(rep["kpis"][:4])
    summary = (rep.get("onepager_summary") or (rep.get("executive_summary") or "").split("\n\n")[0])
    W.p(summary, size=10.5, after=8)
    if rep.get("top_priorities"):
        e = W.p(t["priorities"].upper(), size=8.5, bold=True, color=c.get("eyebrow", c["primary"]), after=2)
        for r in e.runs:
            letter_spacing(r, 30)
        for pr in rep["top_priorities"][:3]:
            W.numbered(pr)
    W.p(after=4)
    W.callout(rep.get("cta_text") or brand.get("cta_text", ""), title=rep.get("cta_title") or brand.get("cta_title", t["next"]))
    W.p(brand.get("cta_url", ""), bold=True, color=c.get("primary_soft", c["primary"]), align="center")
    W.doc.save(out_docx)
    return out_docx


def install_fonts():
    src = os.path.join(ASSETS, "fonts")
    if not os.path.isdir(src):
        return
    dst = os.path.expanduser("~/.local/share/fonts/carratu-skill")
    try:
        os.makedirs(dst, exist_ok=True)
        new = False
        for f in os.listdir(src):
            if f.lower().endswith((".ttf", ".otf")) and not os.path.exists(os.path.join(dst, f)):
                shutil.copy(os.path.join(src, f), dst)
                new = True
        if new and shutil.which("fc-cache"):
            subprocess.run(["fc-cache", "-f", dst], capture_output=True, timeout=60)
    except Exception as e:
        print(f"Aviso: fontes não instaladas ({e})", file=sys.stderr)


def to_pdf(docx_path, out_dir):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    install_fonts()
    try:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
                       check=True, capture_output=True, timeout=180)
    except Exception as e:
        print(f"PDF falhou: {e}", file=sys.stderr)
        return None
    pdf = os.path.splitext(docx_path)[0] + ".pdf"
    return pdf if os.path.exists(pdf) else None


def slug(s):
    s = norm(s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "relatorio"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json")
    ap.add_argument("--auto", action="append", default=[], help="blocos calculados (pode repetir)")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--format", choices=["full", "onepager", "both"], default="full")
    ap.add_argument("--brand", default=os.path.join(ASSETS, "brand.json"))
    ap.add_argument("--onepager-brand", default=None)
    ap.add_argument("--name", default=None, help="nome base do arquivo")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()

    rep = json.load(open(a.report_json, encoding="utf-8"))
    base_dir = os.path.dirname(os.path.abspath(a.report_json))
    brand = json.load(open(a.brand, encoding="utf-8"))
    brand["_dir"] = os.path.dirname(os.path.abspath(a.brand))
    autos = []
    for p in a.auto:
        d = json.load(open(p, encoding="utf-8"))
        d["_dir"] = os.path.dirname(os.path.abspath(p))
        autos.append(d)
    os.makedirs(a.out, exist_ok=True)
    name = a.name or slug(f"{rep.get('file_prefix') or rep.get('title', 'relatorio')}-{rep.get('client_name', '')}")
    made = []
    if a.format in ("full", "both"):
        made.append(build_full(rep, autos, brand, os.path.join(a.out, name + ".docx"), base_dir))
    if a.format in ("onepager", "both"):
        opb = a.onepager_brand or (os.path.join(brand["_dir"], brand["onepager_brand"]) if brand.get("onepager_brand") else a.brand)
        ob = json.load(open(opb, encoding="utf-8"))
        ob["_dir"] = os.path.dirname(os.path.abspath(opb))
        made.append(build_onepager(rep, ob, os.path.join(a.out, name + "-1pag.docx")))
    for d in list(made):
        if not a.no_pdf:
            pdf = to_pdf(d, a.out)
            if pdf:
                made.append(pdf)
    for m in made:
        print(m)


if __name__ == "__main__":
    main()
