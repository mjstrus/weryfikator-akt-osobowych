# pdf_generator.py – Generowanie raportów PDF (ReportLab)

import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import ABACUS, LEGAL_CONSEQUENCES
from scoring import RISK_COLORS, RISK_EMOJI

# ---------- Font registration ----------
_BASE_DIR = os.path.dirname(__file__)
_FONT_PATH = os.path.join(_BASE_DIR, "DejaVuSans.ttf")
_FONT_BOLD_PATH = os.path.join(_BASE_DIR, "DejaVuSans-Bold.ttf")

FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

if os.path.exists(_FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", _FONT_PATH))
        FONT_NAME = "DejaVuSans"
    except Exception:
        pass

if os.path.exists(_FONT_BOLD_PATH):
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _FONT_BOLD_PATH))
        FONT_BOLD = "DejaVuSans-Bold"
    except Exception:
        pass

# ---------- Colors ----------
NAVY = colors.HexColor("#0d1b2a")
NAVY2 = colors.HexColor("#1b2d45")
LIGHT_GRAY = colors.HexColor("#f4f6f8")
BORDER_GRAY = colors.HexColor("#dee2e6")
RED = colors.HexColor("#e74c3c")
ORANGE = colors.HexColor("#f39c12")
GREEN = colors.HexColor("#27ae60")
WHITE = colors.white

RISK_COLOR_MAP = {
    "niskie": GREEN,
    "średnie": ORANGE,
    "wysokie": RED,
}


# ---------- Styles ----------
def _styles():
    ss = getSampleStyleSheet()

    base = dict(fontName=FONT_NAME, fontSize=10, leading=14)
    bold_base = dict(fontName=FONT_BOLD, fontSize=10, leading=14)

    styles = {
        "title": ParagraphStyle(
            "title",
            fontName=FONT_BOLD,
            fontSize=18,
            leading=24,
            textColor=WHITE,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName=FONT_NAME,
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#cfd8e3"),
            spaceAfter=2,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName=FONT_BOLD,
            fontSize=12,
            leading=16,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle("normal", **base, spaceAfter=4),
        "bold": ParagraphStyle("bold", **bold_base, spaceAfter=4),
        "small": ParagraphStyle(
            "small",
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.gray,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.gray,
            alignment=1,
        ),
        "legal": ParagraphStyle(
            "legal",
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#333333"),
            spaceAfter=4,
        ),
    }
    return styles


# ---------- Header / Footer callback ----------
class _HeaderFooter:
    def __init__(self, audyt: dict, styles: dict):
        self.audyt = audyt
        self.styles = styles

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = A4

        # Footer line
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, 1.8 * cm, w - 1.5 * cm, 1.8 * cm)

        # Footer text
        canvas.setFont(FONT_NAME, 7)
        canvas.setFillColor(colors.gray)
        abacus_line = (
            f"{ABACUS['nazwa']}  |  {ABACUS['adres']}  |  "
            f"{ABACUS['www']}  |  {ABACUS['email']}  |  tel. {ABACUS['tel']}"
        )
        canvas.drawCentredString(w / 2, 1.4 * cm, abacus_line)
        canvas.drawRightString(w - 1.5 * cm, 1.0 * cm, f"Strona {doc.page}")

        canvas.restoreState()


# ---------- Helper builders ----------
def _employee_info_table(audyt: dict, styles: dict):
    data = [
        ["Firma / Pracodawca", audyt.get("firma", "—")],
        ["Imię i nazwisko", f"{audyt.get('imie', '')} {audyt.get('nazwisko', '')}"],
        ["Stanowisko", audyt.get("stanowisko", "—")],
        ["Data zatrudnienia", audyt.get("data_zatrudnienia", "—")],
        ["PESEL", audyt.get("pesel", "—")],
        ["Status pracownika", audyt.get("status_pracownika", "—").capitalize()],
    ]
    if audyt.get("wymiar_etatu"):
        data.append(["Wymiar etatu", audyt["wymiar_etatu"]])
    if audyt.get("minimalne_wynagrodzenie"):
        data.append(["Min. wynagrodzenie", audyt["minimalne_wynagrodzenie"]])

    tbl = Table(data, colWidths=[5 * cm, 11.5 * cm])
    tbl.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GRAY),
            ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER_GRAY),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return tbl


def _risk_summary_table(scores: dict, styles: dict):
    risk = scores["risk_level"]
    rc = RISK_COLOR_MAP.get(risk, GREEN)
    emoji = RISK_EMOJI.get(risk, "")

    data = [
        ["Wskaźnik", "Wartość"],
        ["Braki obowiązkowe", f"{scores['obligatory_gaps']} / {scores['obligatory_total']}"],
        ["Braki warunkowe", f"{scores['conditional_gaps']} / {scores['conditional_total']}"],
        ["Braki dobrowolne", f"{scores['voluntary_gaps']} / {scores['voluntary_total']}"],
        ["Kompletność dokumentacji", f"{scores['completeness']}%"],
        ["% braków obowiązkowych", f"{scores['risk_pct']}%"],
        ["Poziom ryzyka", f"{emoji} {risk.upper()}"],
    ]

    tbl = Table(data, colWidths=[8 * cm, 8.5 * cm])
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, -1), (-1, -1), rc),
        ("TEXTCOLOR", (0, -1), (-1, -1), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
    tbl.setStyle(style)
    return tbl


def _gap_table(gap_list: list, styles: dict):
    STATUS_COLORS = {
        "obowiązkowe": colors.HexColor("#fde8e8"),
        "warunkowe": colors.HexColor("#fef9e7"),
        "dobrowolne": colors.HexColor("#eafaf1"),
    }
    STATUS_LABELS = {
        "obowiązkowe": "OBL",
        "warunkowe": "WAR",
        "dobrowolne": "DOB",
    }

    header = ["ID", "Opis dokumentu", "Typ", "Status braku", "Rekomendacja"]
    data = [header]

    for g in gap_list:
        gs_label = "BRAK" if g["gap_status"] == "brak" else "WERYFIKACJA"
        data.append([
            g["id"],
            Paragraph(g["text"], ParagraphStyle("cell", fontName=FONT_NAME, fontSize=8, leading=11)),
            STATUS_LABELS.get(g["status"], "?"),
            gs_label,
            Paragraph(g["recommendation"], ParagraphStyle("rec", fontName=FONT_NAME, fontSize=8, leading=11)),
        ])

    tbl = Table(data, colWidths=[1.2 * cm, 7.5 * cm, 1.2 * cm, 2.2 * cm, 4.4 * cm])
    ts = TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])

    for i, g in enumerate(gap_list, start=1):
        bg = STATUS_COLORS.get(g["status"], WHITE)
        ts.add("BACKGROUND", (0, i), (-1, i), bg)

    tbl.setStyle(ts)
    return tbl


def _title_block(styles: dict):
    """Kolorowy baner tytułowy."""
    data = [[
        Paragraph("AUDYT TECZEK AKT OSOBOWYCH", styles["title"]),
    ], [
        Paragraph("z rekomendacjami", styles["subtitle"]),
    ], [
        Paragraph(f"{ABACUS['nazwa']}", styles["subtitle"]),
    ]]
    tbl = Table(data, colWidths=[17 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 16),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
    ]))
    return tbl


# ---------- Public API ----------

def generate_individual_pdf(audyt: dict, scores: dict) -> bytes:
    """Generuje indywidualny raport PDF dla pracownika."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title=f"Audyt – {audyt.get('imie')} {audyt.get('nazwisko')}",
        author=ABACUS["nazwa"],
    )

    styles = _styles()
    hf = _HeaderFooter(audyt, styles)
    story = []

    # --- Baner tytułowy ---
    story.append(_title_block(styles))
    story.append(Spacer(1, 0.5 * cm))

    # --- Data raportu ---
    story.append(
        Paragraph(
            f"Data weryfikacji: <b>{audyt.get('data_weryfikacji', '—')}</b> &nbsp;&nbsp; "
            f"Weryfikujący: <b>{audyt.get('weryfikujacy_imie_nazwisko', '—')}</b> "
            f"({audyt.get('weryfikujacy_stanowisko', '—')})",
            styles["small"],
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # --- Dane pracownika ---
    story.append(Paragraph("Dane pracownika", styles["section_header"]))
    story.append(_employee_info_table(audyt, styles))
    story.append(Spacer(1, 0.4 * cm))

    # --- Wynik audytu ---
    story.append(Paragraph("Wynik audytu – podsumowanie ryzyka", styles["section_header"]))
    story.append(_risk_summary_table(scores, styles))
    story.append(Spacer(1, 0.4 * cm))

    # --- Braki ---
    gap_list = scores.get("gap_list", [])
    if gap_list:
        story.append(Paragraph(f"Lista braków dokumentacyjnych ({len(gap_list)} poz.)", styles["section_header"]))
        story.append(_gap_table(gap_list, styles))
        story.append(Spacer(1, 0.4 * cm))
    else:
        story.append(
            Paragraph("✅ Brak stwierdzonych braków dokumentacyjnych.", styles["normal"])
        )
        story.append(Spacer(1, 0.4 * cm))

    # --- Konsekwencje prawne ---
    story.append(PageBreak())
    story.append(Paragraph("Konsekwencje prawne – informacja", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
    story.append(Spacer(1, 0.2 * cm))

    for line in LEGAL_CONSEQUENCES.strip().split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.15 * cm))
            continue
        if line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(line.replace("**", ""), styles["bold"]))
        elif line.startswith("•"):
            story.append(Paragraph(line, styles["legal"]))
        else:
            story.append(Paragraph(line, styles["legal"]))

    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            f"Raport wygenerowany automatycznie przez system audytowy {ABACUS['nazwa']} "
            f"dnia {datetime.now().strftime('%d.%m.%Y o %H:%M')}.",
            styles["small"],
        )
    )

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


def generate_aggregate_pdf(audyty: list[dict]) -> bytes:
    """Generuje zbiorczy raport PDF dla wszystkich/wyfiltrowanych audytów."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        title="Raport zbiorczy – Audyt Akt Osobowych",
        author=ABACUS["nazwa"],
    )

    styles = _styles()

    def hf_cb(canvas, doc_):
        canvas.saveState()
        w, h = A4
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.5)
        canvas.line(1.5 * cm, 1.8 * cm, w - 1.5 * cm, 1.8 * cm)
        canvas.setFont(FONT_NAME, 7)
        canvas.setFillColor(colors.gray)
        abacus_line = (
            f"{ABACUS['nazwa']}  |  {ABACUS['adres']}  |  "
            f"{ABACUS['www']}  |  {ABACUS['email']}  |  tel. {ABACUS['tel']}"
        )
        canvas.drawCentredString(w / 2, 1.4 * cm, abacus_line)
        canvas.drawRightString(w - 1.5 * cm, 1.0 * cm, f"Strona {doc_.page}")
        canvas.restoreState()

    story = []
    story.append(_title_block(styles))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"Raport zbiorczy – {len(audyty)} pracownik(ów) | wygenerowano: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            styles["small"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # Tabela zbiorcza
    header = [
        "Firma", "Pracownik", "Stanowisko", "Status",
        "Braki\nOBL", "Braki\nWAR", "Braki\nDOB",
        "Komplet.", "Ryzyko",
    ]
    data = [header]

    RISK_BG = {"niskie": colors.HexColor("#eafaf1"), "średnie": colors.HexColor("#fef9e7"), "wysokie": colors.HexColor("#fde8e8")}

    row_risk = []
    for a in audyty:
        row = [
            a.get("firma", "—"),
            f"{a.get('imie','')} {a.get('nazwisko','')}",
            a.get("stanowisko", "—"),
            a.get("status_pracownika", "—"),
            str(a.get("braki_obowiazkowe", 0)),
            str(a.get("braki_warunkowe", 0)),
            str(a.get("braki_dobrowolne", 0)),
            f"{a.get('kompletnosc_procent', 100):.1f}%",
            a.get("poziom_ryzyka", "niskie").upper(),
        ]
        data.append(row)
        row_risk.append(a.get("poziom_ryzyka", "niskie"))

    col_widths = [3.5 * cm, 3.5 * cm, 3 * cm, 1.5 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm, 1.5 * cm, 1.4 * cm]

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    ts = TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER_GRAY),
        ("ALIGN", (4, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ])

    for i, risk in enumerate(row_risk, start=1):
        bg = RISK_BG.get(risk, WHITE)
        ts.add("BACKGROUND", (8, i), (8, i), bg)

    tbl.setStyle(ts)
    story.append(tbl)

    doc.build(story, onFirstPage=hf_cb, onLaterPages=hf_cb)
    return buf.getvalue()
