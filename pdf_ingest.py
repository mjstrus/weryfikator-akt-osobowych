"""
pdf_ingest.py
=============
Zbiorcze wczytywanie plików PDF i wstępna (asystowana) weryfikacja kompletności
teczki akt osobowych.

Założenia projektowe:
- KLASYFIKACJA LOKALNA. Tekst nie opuszcza maszyny (RODO). Brak LLM domyślnie.
- OCR jako fallback dla skanów (pytesseract + pdf2image). Działa też bez OCR,
  wtedy klasyfikuje tylko PDF-y z warstwą tekstową.
- WYNIK = SUGESTIA, nie werdykt. Audytor zatwierdza. Statusy: obecny / do_weryfikacji / brak.
- Pooling: tekst ze wszystkich wrzuconych plików jest łączony, więc działa
  zarówno "1 plik = 1 dokument", jak i "cała teczka w jednym skanie".

Zależności (dodaj do requirements.txt):
    pdfplumber
    pytesseract        # opcjonalnie, do OCR skanów
    pdf2image          # opcjonalnie, do OCR skanów
System (dla OCR):
    tesseract-ocr, tesseract-ocr-pol, poppler-utils
"""

from __future__ import annotations

import difflib
import io
import re
import unicodedata
from dataclasses import dataclass, field

import pdfplumber

# --- OCR jest opcjonalny: jeśli brak bibliotek, moduł nadal działa bez OCR ---
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import ImageOps, ImageFilter
    _OCR_AVAILABLE = True
except Exception:  # noqa: BLE001 - świadomie szeroki, brak OCR nie ma blokować apki
    _OCR_AVAILABLE = False

# DPI renderowania skanów do OCR. 300 = lepsza jakość na drobnym druku/pieczątkach,
# kosztem czasu i pamięci (istotne na Streamlit Cloud przy dużych teczkach).
_OCR_DPI = 300
# Konfiguracja Tesseract: OEM 1 = silnik LSTM, PSM 3 = automatyczna segmentacja strony.
_TESS_CONFIG = "--oem 1 --psm 3"


# ---------------------------------------------------------------------------
# 1. EKSTRAKCJA TEKSTU
# ---------------------------------------------------------------------------

# Poniżej tej liczby znaków na stronie uznajemy PDF za skan i włączamy OCR.
_MIN_CHARS_PER_PAGE = 40


def normalize(text: str) -> str:
    """Małe litery, zdejmij ogonki (ą->a), spłaszcz białe znaki.

    Dzięki zdjęciu ogonków dopasowanie jest odporne na błędy OCR i braki polskich
    znaków, a sygnatury piszemy bez ogonków.
    """
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text)
    return text


# --- Dopasowanie rozmyte: odporne na literówki OCR ('zatrudnienia' vs 'zatrucinienia') ---

# Krótkie / niedystynktywne słowa pomijamy przy dopasowaniu.
_STOP = {"oraz", "celow", "danych", "osoby", "ubiegajacej", "nastepujace", "strony"}


def _tokens(text: str) -> list[str]:
    """Tokeny o długości >=4, bez słów stopowych — tylko nośniki znaczenia."""
    return [t for t in normalize(text).split() if len(t) >= 4 and t not in _STOP]


def _token_present(tok: str, ocr_set: set[str], ocr_list: list[str]) -> bool:
    """Token uznajemy za obecny, gdy jest dokładnie albo ma bliski odpowiednik
    (próg 0.82 = tolerancja ~1-2 błędów OCR na słowo)."""
    if tok in ocr_set:
        return True
    return bool(difflib.get_close_matches(tok, ocr_list, n=1, cutoff=0.82))


def _phrase_matches(phrase: str, ocr_set: set[str], ocr_list: list[str],
                    threshold: float = 0.7) -> bool:
    """Fraza 'liczy się', gdy >=70% jej tokenów odnajdzie się (rozmyto) w tekście.
    Pozwala to przeżyć zgubione lub przekręcone przez OCR słowa."""
    toks = _tokens(phrase)
    if not toks:
        return False
    hits = sum(1 for t in toks if _token_present(t, ocr_set, ocr_list))
    return hits / len(toks) >= threshold


def _preprocess_for_ocr(img):
    """Przygotowanie skanu pod OCR — największa dźwignia jakości przy skanach.

    Skala szarości -> autokontrast -> wyostrzenie. Małe skany powiększamy,
    bo Tesseract lubi większy tekst. Przy braku PIL zwraca obraz bez zmian.
    """
    try:
        img = ImageOps.grayscale(img)
        img = ImageOps.autocontrast(img)
        if min(img.size) < 1500:  # dobij rozdzielczość drobnego druku
            scale = 1500 / min(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        img = img.filter(ImageFilter.SHARPEN)
    except Exception:  # noqa: BLE001 - preprocessing jest best-effort
        pass
    return img


def extract_text_from_pdf(pdf_bytes: bytes, use_ocr: bool = True) -> str:
    """Zwraca tekst całego PDF-u. Jeśli warstwa tekstowa jest pusta (skan)
    i OCR jest dostępny, renderuje strony i puszcza je przez OCR."""
    parts: list[str] = []
    needs_ocr = False

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                parts.append(page_text)
                if len(page_text.strip()) < _MIN_CHARS_PER_PAGE:
                    needs_ocr = True
    except Exception:  # noqa: BLE001 - uszkodzony PDF nie powinien wywalać apki
        needs_ocr = True

    text = "\n".join(parts).strip()

    if needs_ocr and use_ocr and _OCR_AVAILABLE:
        try:
            images = convert_from_bytes(pdf_bytes, dpi=_OCR_DPI)
            ocr_parts = [
                pytesseract.image_to_string(
                    _preprocess_for_ocr(img), lang="pol", config=_TESS_CONFIG
                )
                for img in images
            ]
            ocr_text = "\n".join(ocr_parts).strip()
            # OCR uzupełnia, nie nadpisuje (część stron może mieć tekst natywny)
            if len(ocr_text) > len(text):
                text = ocr_text
        except Exception:  # noqa: BLE001
            pass  # zostaw to, co udało się wyciągnąć natywnie

    return text


# ---------------------------------------------------------------------------
# 2. SYGNATURY DOKUMENTÓW
# ---------------------------------------------------------------------------
# To jest serce funkcji i JEDYNE miejsce wymagające Twojej wiedzy dziedzinowej.
# - keywords:       frazy charakterystyczne (bez ogonków, małe litery)
# - filename_hints: fragmenty nazwy pliku, które mocno podbijają pewność
# - satisfies:      ID pytań z config.py, które ten dokument "zalicza"
# - required:       czy brak tego dokumentu to brak OBOWIĄZKOWY (do scoringu)
#
# Mapowanie zsynchronizowane z config.py (commit main). Pytania wieloopcjowe
# (B7, B9, B10, B12, B18, B19, B21, P5, C4) nigdy nie dostają automatycznie "TAK"
# — patrz suggested_answers(): obecność druku nie rozstrzyga opcji "stosowane /
# zweryfikowano z listą płac", więc takie pozycje zawsze idą do weryfikacji.
# Dokumentów o nierozpoznawalnej treści (A2 CV, A4 kwalifikacje) NIE wykrywamy
# po treści — wpadną w "brak/do weryfikacji" i wymagają ręcznego sprawdzenia.

@dataclass
class DocSignature:
    id: str
    label: str
    keywords: list[str]
    satisfies: list[str] = field(default_factory=list)
    filename_hints: list[str] = field(default_factory=list)
    required: bool = True


DOC_SIGNATURES: list[DocSignature] = [
    # --- Część A: rekrutacja ---
    DocSignature(
        id="kwestionariusz_kandydat", label="Kwestionariusz osobowy kandydata",
        keywords=["kwestionariusz osobowy", "osoby ubiegajacej sie o zatrudnienie"],
        filename_hints=["kwestionariusz", "kandydat"], satisfies=["A1"],
    ),
    DocSignature(
        id="skierowanie_badania", label="Skierowanie na badania wstępne",
        keywords=["skierowanie na badania lekarskie", "badania wstepne",
                  "badania profilaktyczne"],
        filename_hints=["skierowanie", "badania"], satisfies=["A5"],
    ),
    DocSignature(
        id="orzeczenie_lekarskie", label="Orzeczenie lekarskie dopuszczające do pracy",
        keywords=["orzeczenie lekarskie", "brak przeciwwskazan", "zdolny do pracy"],
        filename_hints=["orzeczenie", "lekarsk"], satisfies=["A6"],
    ),
    # --- Część B: zatrudnienie ---
    DocSignature(
        id="kwestionariusz_pracownik", label="Kwestionariusz osoby zatrudnionej",
        keywords=["kwestionariusz osobowy dla pracownika", "osoby zatrudnionej"],
        filename_hints=["kwestionariusz pracownik"], satisfies=["B1"],
    ),
    DocSignature(
        id="zgoda_rodo", label="Zgoda na przetwarzanie danych (RODO)",
        keywords=["zgoda na przetwarzanie danych osobowych",
                  "przetwarzanie danych osobowych"],
        filename_hints=["rodo", "zgoda"], satisfies=["B2"],
    ),
    DocSignature(
        id="umowa_o_prace", label="Umowa o pracę",
        keywords=["umowa o prace", "rodzaj umowy", "wynagrodzenie zasadnicze"],
        filename_hints=["umowa", "uop"], satisfies=["B3"],
    ),
    DocSignature(
        id="informacja_art29", label="Informacja o warunkach zatrudnienia",
        keywords=["informacja o warunkach zatrudnienia", "warunkach zatrudnienia"],
        filename_hints=["informacja", "art29", "warunki"], satisfies=["B4"],
    ),
    DocSignature(
        id="zakres_obowiazkow", label="Zakres obowiązków",
        keywords=["zakres obowiazkow", "zakres czynnosci"],
        filename_hints=["zakres", "obowiazki"], satisfies=["B5"],
    ),
    DocSignature(
        id="bhp", label="Szkolenie BHP – potwierdzenie odbycia",
        keywords=["szkolenie w dziedzinie bhp", "karta szkolenia bhp",
                  "instruktaz stanowiskowy"],
        filename_hints=["bhp", "szkolenie"], satisfies=["B6"],
    ),
    DocSignature(
        id="pit2", label="PIT-2 (oświadczenie pracownika)",
        keywords=["pit-2", "oswiadczenie pracownika dla celow obliczania",
                  "kwote zmniejszajaca podatek"],
        filename_hints=["pit2", "pit-2"], satisfies=["B7"],
    ),
    DocSignature(
        id="rowne_traktowanie", label="Informacja dot. równego traktowania",
        keywords=["rownym traktowaniu w zatrudnieniu", "rowne traktowanie"],
        filename_hints=["rowne", "traktowanie"], satisfies=["B8"],
    ),
    DocSignature(
        id="kup", label="Oświadczenie KUP (koszty uzyskania przychodu)",
        keywords=["koszty uzyskania przychodu", "podwyzszone koszty uzyskania"],
        filename_hints=["kup", "koszty"], satisfies=["B9"],
    ),
    DocSignature(
        id="fp", label="Oświadczenie FP (Fundusz Pracy)",
        keywords=["fundusz pracy"],
        filename_hints=["fp", "fundusz"], satisfies=["B10"], required=False,
    ),
    DocSignature(
        id="regulamin_pracy", label="Potwierdzenie zapoznania z regulaminem pracy",
        keywords=["zapoznalem sie z regulaminem pracy", "regulaminem pracy"],
        filename_hints=["regulamin"], satisfies=["B11"],
    ),
    DocSignature(
        id="sposob_wyplaty", label="Oświadczenie o sposobie wypłaty wynagrodzenia",
        keywords=["wyplaty wynagrodzenia", "na rachunek bankowy", "numer rachunku"],
        filename_hints=["wyplata", "rachunek", "konto"], satisfies=["B12"],
    ),
    DocSignature(
        id="obwieszczenie_czas_pracy",
        label="Obwieszczenie o systemie i rozkładzie czasu pracy",
        keywords=["obwieszczenie", "systemie i rozkladzie czasu pracy"],
        filename_hints=["obwieszczenie"], satisfies=["B15"],
    ),
    DocSignature(
        id="zgloszenie_rodzina_zdrowotne",
        label="Wniosek o zgłoszenie członka rodziny do ubezp. zdrowotnego",
        keywords=["zgloszenie czlonka rodziny", "ubezpieczenia zdrowotnego"],
        filename_hints=["czlonek rodziny", "zdrowotne"], satisfies=["B16"],
        required=False,
    ),
    DocSignature(
        id="ppk", label="Deklaracja PPK",
        keywords=["pracownicze plany kapitalowe", "deklaracja ppk", "rezygnacja ppk"],
        filename_hints=["ppk"], satisfies=["B18"], required=False,
    ),
    DocSignature(
        id="aneks", label="Aneks do umowy o pracę",
        keywords=["aneks do umowy o prace", "aneks nr"],
        filename_hints=["aneks"], satisfies=["B19"],
    ),
    DocSignature(
        id="wniosek_urlopowy", label="Wniosek urlopowy",
        keywords=["wniosek o urlop", "urlopu wypoczynkowego"],
        filename_hints=["urlop", "wniosek urlop"], satisfies=["B21"],
    ),
    # --- Część C: ustanie zatrudnienia (były pracownik) ---
    DocSignature(
        id="rozwiazanie_umowy", label="Rozwiązanie umowy o pracę",
        keywords=["rozwiazanie umowy o prace", "za wypowiedzeniem",
                  "za porozumieniem stron"],
        filename_hints=["rozwiazanie", "wypowiedzenie"], satisfies=["C1"],
    ),
    DocSignature(
        id="swiadectwo_pracy", label="Świadectwo pracy / potwierdzenie odbioru",
        keywords=["swiadectwo pracy", "potwierdzam odbior swiadectwa"],
        filename_hints=["swiadectwo"], satisfies=["C2"],
    ),
    # --- Dokumentacja pozaaktowa (P) ---
    DocSignature(
        id="ewidencja_czasu", label="Ewidencja czasu pracy",
        keywords=["ewidencja czasu pracy"],
        filename_hints=["ewidencja"], satisfies=["P1"],
    ),
    DocSignature(
        id="karty_urlopowe", label="Karty urlopowe",
        keywords=["karta urlopowa"],
        filename_hints=["karta urlop"], satisfies=["P2"],
    ),
    DocSignature(
        id="listy_obecnosci", label="Listy obecności",
        keywords=["lista obecnosci"],
        filename_hints=["obecnosc"], satisfies=["P3"],
    ),
    DocSignature(
        id="lista_plac", label="Lista płac",
        keywords=["lista plac"],
        filename_hints=["lista plac", "place"], satisfies=["P4"],
    ),
    DocSignature(
        id="zasilki", label="Dokumentacja zasiłkowa (ZUS, L4)",
        keywords=["zwolnienie lekarskie", "zasilek chorobowy", "zus zla"],
        filename_hints=["zasilek", "l4", "zwolnienie"], satisfies=["P7"],
    ),
    DocSignature(
        id="zus_zua", label="ZUS ZUA (zgłoszenie do ubezpieczeń)",
        keywords=["zus zua", "zgloszenie do ubezpieczen"],
        filename_hints=["zua"], satisfies=["P9"],
    ),
    DocSignature(
        id="zus_zwua", label="ZUS ZWUA (wyrejestrowanie z ubezpieczeń)",
        keywords=["zus zwua", "wyrejestrowanie z ubezpieczen"],
        filename_hints=["zwua"], satisfies=["P10"],
    ),
    DocSignature(
        id="zus_zcna", label="ZUS ZCNA (zgłoszenie członka rodziny)",
        keywords=["zus zcna", "zgloszenie danych o czlonkach rodziny"],
        filename_hints=["zcna"], satisfies=["P11"], required=False,
    ),
    # --- Dodatkowe sygnatury obowiązkowych dokumentów (zmniejszają martwe pola) ---
    DocSignature(
        id="zapoznanie_obwieszczenie",
        label="Oświadczenie o zapoznaniu się z obwieszczeniem",
        keywords=["zapoznaniu sie z obwieszczeniem", "zapoznalem sie z obwieszczeniem"],
        filename_hints=["zapoznanie obwieszczenie"], satisfies=["B17"],
    ),
    DocSignature(
        id="karty_przychodow", label="Karty przychodów zatrudnionych",
        keywords=["karta przychodow", "karty przychodow"],
        filename_hints=["przychody", "karta przychod"], satisfies=["P8"],
    ),
    DocSignature(
        id="wyplata_do_rak", label="Wniosek o wypłatę wynagrodzenia do rąk własnych",
        keywords=["do rak wlasnych", "wyplata do rak wlasnych"],
        filename_hints=["do rak wlasnych", "gotowka"], satisfies=["P5"],
    ),
]

# Pytania wieloopcjowe — obecność dokumentu NIE rozstrzyga ich wartości,
# więc nawet przy pewnym wykryciu sugerujemy tylko "do weryfikacji".
# (typy z config.ANS: lp_5, wyplata_3, wyplata_4, aneksy, wnioski_url, ekwiwalent)
NON_BINARY_QUESTIONS = {"B7", "B9", "B10", "B12", "B18", "B19", "B21", "P5", "C4"}


# ---------------------------------------------------------------------------
# 3. KLASYFIKACJA
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    sig: DocSignature
    status: str          # "obecny" | "do_weryfikacji" | "brak"
    score: int           # surowa liczba trafień (do debugowania)
    evidence: list[str]  # które frazy / nazwy plików trafiły


def detect_documents(corpus_text: str, filenames: list[str]) -> list[Detection]:
    """Sprawdza obecność KAŻDEGO znanego typu dokumentu w połączonym tekście.

    Logika progu:
      >=2 sygnały  -> "obecny"        (wysoka pewność)
       1 sygnał    -> "do_weryfikacji" (audytor musi spojrzeć)
       0 sygnałów  -> "brak"
    Trafienie w nazwie pliku liczy się jako sygnał silny (waga 2).
    """
    norm_text = normalize(corpus_text)
    norm_names = normalize(" ".join(filenames))
    # Pula tokenów z OCR — liczona raz, używana do rozmytego dopasowania fraz.
    ocr_list = [t for t in norm_text.split() if len(t) >= 4]
    ocr_set = set(ocr_list)

    detections: list[Detection] = []
    for sig in DOC_SIGNATURES:
        score = 0
        evidence: list[str] = []

        for kw in sig.keywords:
            if _phrase_matches(kw, ocr_set, ocr_list):
                score += 1
                evidence.append(f"fraza: '{kw}'")

        for hint in sig.filename_hints:
            if hint in norm_names:
                score += 2
                evidence.append(f"nazwa pliku: '{hint}'")

        if score >= 2:
            status = "obecny"
        elif score == 1:
            status = "do_weryfikacji"
        else:
            status = "brak"

        detections.append(Detection(sig=sig, status=status, score=score, evidence=evidence))

    return detections


def suggested_answers(detections: list[Detection]) -> dict[str, str]:
    """Mapuje wykryte dokumenty na SUGEROWANE odpowiedzi pytań formularza.

    Zwraca {ID_pytania: "TAK" | "?"}. Pytania nieobjęte żadną sygnaturą
    pozostaw w aplikacji bez zmian (audytor wypełnia ręcznie).

    Reguła pytań wieloopcjowych: dla NON_BINARY_QUESTIONS nigdy nie zwracamy
    "TAK" — obecność druku nie rozstrzyga opcji typu "stosowane / zweryfikowano
    z listą płac". Takie pytania zawsze dostają "?" (do weryfikacji).
    """
    answers: dict[str, str] = {}
    for det in detections:
        if det.status == "brak":
            continue
        for qid in det.sig.satisfies:
            if qid in NON_BINARY_QUESTIONS:
                value = "?"  # wymaga decyzji audytora niezależnie od pewności
            else:
                value = "TAK" if det.status == "obecny" else "?"
            # "TAK" wygrywa z "?", gdy ten sam dokument trafia w kilka sygnatur
            if answers.get(qid) != "TAK":
                answers[qid] = value
    return answers


# ---------------------------------------------------------------------------
# 4. INTEGRACJA ZE STREAMLIT (wywołaj w app.py)
# ---------------------------------------------------------------------------

def render_bulk_upload(st) -> dict[str, str] | None:
    """Renderuje sekcję zbiorczego wgrywania PDF i zwraca sugerowane odpowiedzi.

    Użycie w app.py:
        import pdf_ingest
        suggestions = pdf_ingest.render_bulk_upload(st)
        if suggestions:
            st.session_state["prefill"] = suggestions   # użyj do wstępnego
                                                         # wypełnienia formularza
    """
    st.subheader("📤 Zbiorcze wczytanie dokumentów (PDF)")
    if not _OCR_AVAILABLE:
        st.info("OCR niedostępny — skany bez warstwy tekstowej nie zostaną rozpoznane. "
                "Zainstaluj tesseract-ocr, tesseract-ocr-pol, poppler-utils oraz "
                "pakiety pytesseract i pdf2image.")

    files = st.file_uploader(
        "Wrzuć pliki PDF (możesz zaznaczyć wiele naraz lub całą teczkę w jednym PDF)",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if not files:
        return None

    if not st.button("🔍 Analizuj dokumenty"):
        return None

    corpus_parts: list[str] = []
    filenames: list[str] = []
    progress = st.progress(0.0)
    for i, f in enumerate(files):
        filenames.append(f.name)
        corpus_parts.append(extract_text_from_pdf(f.read()))
        progress.progress((i + 1) / len(files))
    progress.empty()

    detections = detect_documents("\n".join(corpus_parts), filenames)

    obecne = [d for d in detections if d.status == "obecny"]
    sprawdz = [d for d in detections if d.status == "do_weryfikacji"]
    braki = [d for d in detections if d.status == "brak"]

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Rozpoznane", len(obecne))
    col2.metric("⚠️ Do weryfikacji", len(sprawdz))
    col3.metric("❌ Brak", len(braki))

    st.markdown("**Szczegóły:**")
    for d in detections:
        icon = {"obecny": "✅", "do_weryfikacji": "⚠️", "brak": "❌"}[d.status]
        with st.expander(f"{icon} {d.sig.label}", expanded=(d.status == "do_weryfikacji")):
            if d.evidence:
                st.write("Sygnały:", ", ".join(d.evidence))
            else:
                st.write("Brak dopasowania w przesłanych plikach.")
            if d.sig.required and d.status == "brak":
                st.warning("Dokument obowiązkowy — potencjalny brak w aktach.")

    st.caption("To są sugestie wspomagające. Ostateczną ocenę zatwierdza audytor.")
    return suggested_answers(detections)
