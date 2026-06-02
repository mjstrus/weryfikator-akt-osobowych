"""
ai_analyzer.py — LOKALNY silnik analizy dokumentów (bez API, RODO-safe).
=======================================================================
Adapter pod interfejs, którego oczekuje app.py -> page_upload_ai():
    analyze_uploaded_files(uploaded, api_key, progress_cb) -> list[result]
    results_to_answers(confirmed) -> dict[q_id, wartość_odpowiedzi]
    FILENAME_PATTERNS -> dict[q_id, list[fragment_nazwy]]

Detekcja delegowana do pdf_ingest (OCR + rozmyte sygnatury). Dane NIE opuszczają
serwera — parametr `api_key` jest przyjmowany dla zgodności sygnatury, ale ignorowany.

Format wyniku (zgodny z oczekiwaniami app.py):
    {
      "filename":    str,
      "document_id": str | None,   # ID pytania z config.QUESTION_MAP
      "status":      "PEWNY" | "WĄTPLIWY",
      "reason":      str,          # uzasadnienie czytelne dla audytora
      "source":      "LOKALNIE",
      "image_png":   bytes | None, # podgląd nagłówka (tylko dla WĄTPLIWY)
    }

OGRANICZENIE: dla pytań wieloopcjowych zależnych od listy płac (PAYROLL_DEPENDENT)
sama obecność druku nie potwierdza "stosowania". Dla typów lp_5/wyplata_4 wstawiamy
"Jest oświadczenie i nie jest stosowane", co scoring.get_gap_status klasyfikuje jako
'wymaga_weryfikacji' — pozycja trafia więc do listy braków jako do sprawdzenia
(nie znika jako 'ok'). needs_payroll_review() zwraca te ID dodatkowo, gdyby UI
chciało je wyróżnić osobno.
"""

from __future__ import annotations

import io

from config import QUESTION_MAP, ANS
import pdf_ingest

# ---------------------------------------------------------------------------
# Mapowanie wartości odpowiedzi per typ pytania (indeksy w config.ANS, żeby
# napisy zgadzały się 1:1 z opcjami radio w formularzu).
# present = dokument wykryty; absent = brak / niewykryty.
# ---------------------------------------------------------------------------
_PRESENT_IDX = {
    "tak_nie": 0,       # "TAK"
    "tak_nie_nd": 0,    # "TAK"
    "lp_5": 1,          # "Jest oświadczenie i nie jest stosowane" -> scoring: wymaga_weryfikacji
    "wyplata_3": 0,     # "TAK"
    "wyplata_4": 1,     # "Jest oświadczenie i nie jest stosowane" -> scoring: wymaga_weryfikacji
    "aneksy": 2,        # "Były aneksy i są w aktach"            (z detekcji – pewne -> ok)
    "wnioski_url": 0,   # "Tak"                                  (z detekcji – pewne -> ok)
    "ekwiwalent": 0,    # "Jest wniosek i wypłacono"            (PLACEHOLDER – "wypłacono" niepewne)
}
_ABSENT_IDX = {
    "tak_nie": 1,       # "NIE"
    "tak_nie_nd": 2,    # "ND"  – warunkowe: brak detekcji traktujemy jak "nie dotyczy",
                        #        żeby nie zawyżać braków obowiązkowych
    "lp_5": 3,          # "Nie ma oświadczenia i nie jest stosowane"
    "wyplata_3": 1,     # "NIE"
    "wyplata_4": 3,     # "Nie ma oświadczenia i nie jest stosowane"
    "aneksy": 0,        # "Nie było aneksów"
    "wnioski_url": 2,   # "Nie, ale urlop nie był wykorzystywany"
    "ekwiwalent": 2,    # "Nie ma wniosku, bo nie należał się"
}

# Pytania, których obecność druku NIE rozstrzyga poprawnej wartości
# (zależne od weryfikacji z listą płac). Wartość "present" to placeholder.
PAYROLL_DEPENDENT = {"B7", "B9", "B10", "B12", "B18", "P5", "C4"}

# Wzorce nazw plików -> ID pytania, zbudowane z sygnatur pdf_ingest.
FILENAME_PATTERNS: dict[str, list[str]] = {
    sig.satisfies[0]: list(sig.filename_hints)
    for sig in pdf_ingest.DOC_SIGNATURES
    if sig.satisfies and sig.filename_hints
}


def _answer_value(ans_type: str, present: bool) -> str:
    """Zwraca napis odpowiedzi zgodny z opcjami radio dla danego typu pytania."""
    table = _PRESENT_IDX if present else _ABSENT_IDX
    opts = ANS.get(ans_type, ["TAK", "NIE"])
    idx = table.get(ans_type, 0 if present else 1)
    return opts[min(idx, len(opts) - 1)]


def _mk_result(filename, document_id, status, reason, image_png=None) -> dict:
    return {
        "filename": filename,
        "document_id": document_id,
        "status": status,
        "reason": reason,
        "source": "LOKALNIE",
        "image_png": image_png,
    }


def _classify_text(text: str, filename: str) -> list[dict]:
    """Klasyfikuje pojedynczy plik (po treści + nazwie). Zwraca 1+ wyników.

    - silne dopasowania (status 'obecny') -> każde jako osobny wynik PEWNY
      (obsługuje przypadek wielu dokumentów w jednym skanie/teczce),
    - tylko słabe ('do_weryfikacji') -> najlepszy jako WĄTPLIWY,
    - brak -> WĄTPLIWY bez przypisania (trafia do kolejki przeglądu).
    """
    dets = pdf_ingest.detect_documents(text, [filename])
    strong = [d for d in dets if d.status == "obecny"]
    weak = sorted((d for d in dets if d.status == "do_weryfikacji"),
                  key=lambda d: -d.score)

    if strong:
        out = []
        for d in strong:
            qid = d.sig.satisfies[0] if d.sig.satisfies else None
            out.append(_mk_result(
                filename, qid, "PEWNY",
                f"Rozpoznano: {d.sig.label} ({'; '.join(d.evidence)})",
            ))
        return out

    if weak:
        d = weak[0]
        qid = d.sig.satisfies[0] if d.sig.satisfies else None
        return [_mk_result(
            filename, qid, "WĄTPLIWY",
            f"Słaby sygnał dla: {d.sig.label} ({'; '.join(d.evidence)}). "
            f"Wymaga potwierdzenia.",
        )]

    return [_mk_result(
        filename, None, "WĄTPLIWY",
        "Nie rozpoznano typu dokumentu na podstawie treści ani nazwy pliku.",
    )]


def _render_header_png(pdf_bytes: bytes) -> bytes | None:
    """Podgląd górnych ~25% pierwszej strony — do oceny wątpliwych przez człowieka.
    Best-effort: bez pdf2image zwraca None (UI to obsługuje warunkowo)."""
    try:
        from pdf2image import convert_from_bytes
        imgs = convert_from_bytes(pdf_bytes, dpi=120, first_page=1, last_page=1)
        if not imgs:
            return None
        img = imgs[0]
        header = img.crop((0, 0, img.width, int(img.height * 0.25)))
        buf = io.BytesIO()
        header.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - podgląd jest opcjonalny
        return None


def analyze_uploaded_files(uploaded, api_key=None, progress_cb=None) -> list[dict]:
    """Analizuje wgrane pliki PDF LOKALNIE.

    api_key — ignorowany (silnik lokalny, dane nie opuszczają serwera).
    progress_cb(current, total, filename) — opcjonalny callback postępu.
    """
    results: list[dict] = []
    total = len(uploaded)

    for i, f in enumerate(uploaded):
        name = getattr(f, "name", f"plik_{i + 1}.pdf")
        if progress_cb:
            progress_cb(i, total, name)

        try:
            f.seek(0)  # bufor mógł być już raz odczytany
        except Exception:  # noqa: BLE001
            pass
        data = f.read()

        text = pdf_ingest.extract_text_from_pdf(data)
        file_results = _classify_text(text, name)

        # Podgląd nagłówka generujemy tylko dla wątpliwych (oszczędność OCR/CPU).
        for r in file_results:
            if r["status"] == "WĄTPLIWY":
                r["image_png"] = _render_header_png(data)

        results.extend(file_results)

    if progress_cb:
        progress_cb(total, total, "")
    return results


def results_to_answers(confirmed: list[dict]) -> dict[str, str]:
    """Buduje słownik odpowiedzi formularza z potwierdzonych wyników.

    KLUCZOWE: startujemy od wartości 'brak' dla KAŻDEGO pytania (inaczej
    niewykryte dokumenty zostałyby policzone jako obecne), a następnie
    nadpisujemy wykryte na 'obecny'. Dzięki temu scoring.calculate_scores
    poprawnie wyłapie braki.
    """
    answers: dict[str, str] = {}
    for qid, q in QUESTION_MAP.items():
        answers[qid] = _answer_value(q.get("ans", "tak_nie"), present=False)

    for r in confirmed:
        qid = r.get("document_id")
        if qid and qid in QUESTION_MAP:
            answers[qid] = _answer_value(QUESTION_MAP[qid].get("ans", "tak_nie"),
                                         present=True)
    return answers


def needs_payroll_review(confirmed: list[dict]) -> list[str]:
    """ID potwierdzonych pytań, których wartość to placeholder wymagający
    weryfikacji z listą płac. UI może to pokazać jako ostrzeżenie."""
    return sorted({
        r["document_id"] for r in confirmed
        if r.get("document_id") in PAYROLL_DEPENDENT
    })
