# ai_analyzer.py – Analiza dokumentów kadrowych przez Claude API
# Strategia: crop top 20% strony → base64 PNG → Claude identyfikuje dokument

import base64
import json
import re
import fitz  # PyMuPDF
import anthropic
from config import QUESTION_MAP

# ─────────────────────────────────────────────
#  SŁOWNIK WZORCÓW NAZW PLIKÓW
# ─────────────────────────────────────────────

FILENAME_PATTERNS: dict[str, list[str]] = {
    "A1": ["kwestionariusz_kandydat", "kw_kandydat", "kandydat"],
    "A2": ["cv", "curriculum_vitae", "zyciorys", "życiorys"],
    "A3": ["list_motywacyjny", "list_mot", "motywacyjny"],
    "A4": ["kwalifikacje", "dyplom", "certyfikat", "swiadectwo_szkol", "wyksztalcenie"],
    "A5": ["skierowanie_badania", "skierowanie_wstepne", "badania_wstepne"],
    "A6": ["orzeczenie_lekarskie", "orzeczenie", "zdolny_do_pracy", "zaswiadczenie_lekarskie"],
    "B1": ["kwestionariusz_zatrudniony", "kw_zatrudniony", "kwestionariusz_osobowy"],
    "B2": ["rodo", "zgoda_dane", "przetwarzanie_danych", "zgoda_rodo"],
    "B3": ["umowa_o_prace", "umowa_pracy", "umowa_prace"],
    "B4": ["informacja_warunki", "warunki_zatrudnienia", "inf_warunki"],
    "B5": ["zakres_obowiazkow", "zakres_czynnosci", "obowiazki"],
    "B6": ["bhp", "szkolenie_bhp", "bezpieczenstwo", "instruktaz_bhp"],
    "B7": ["pit2", "pit_2"],
    "B8": ["rowne_traktowanie", "rownosc", "antydyskryminacja"],
    "B9": ["kup", "koszty_uzyskania", "oświadczenie_kup"],
    "B10": ["fp", "fundusz_pracy", "oswiadczenie_fp"],
    "B11": ["regulamin", "zapoznanie_regulamin", "potwierdzenie_regulamin"],
    "B12": ["wyplata_wynagrodzenia", "sposob_wyplaty", "konto_bankowe", "wyplata"],
    "B13": ["opieka_188", "kp188", "art_188", "opieka_dziecko"],
    "B14": ["powierzenie_mienia", "mienie", "powierzenie"],
    "B15": ["obwieszczenie_czas", "system_pracy", "rozklad_czasu"],
    "B16": ["rodzina_zus", "czlonek_rodziny", "ubezpieczenie_rodziny"],
    "B17": ["zapoznanie_obwieszczenie", "podpisanie_obwieszczenie"],
    "B18": ["ppk", "pracownicze_plany", "deklaracja_ppk"],
    "B19": ["aneks", "aneksy", "zmiana_umowy"],
    "B20": ["zajecie_wierzytelnosci", "komornik", "wierzytelnosc"],
    "B21": ["wniosek_urlopowy", "urlop", "wnioski_urlop"],
    "C1": ["rozwiazanie_umowy", "wypowiedzenie", "rozwiazanie", "swiadectwo_rozw"],
    "C2": ["swiadectwo_pracy", "odbior_swiadectwa", "potwierdzenie_swiadectwa"],
    "C3": ["sprostowanie_swiadectwa", "sprostowanie"],
    "C4": ["ekwiwalent_urlop", "ekwiwalent", "rozliczenie_urlop"],
    "D1": ["kara_porzadkowa", "upomnienie", "nagana", "zawiadomienie_ukaranie"],
    "D2": ["wyjasnienia_pracownik", "wyjasnienia"],
    "D3": ["usuniecie_kary", "kara_usunieta"],
    "E1": ["trzezwosc", "kontrola_trzezwosci", "protokol_trzezwosc", "protokol_trzeźwosc"],
    "E2": ["wyniki_badania", "badanie_trzezwosc"],
    "E3": ["uzasadnienie_kontroli"],
    "P1": ["ewidencja_czasu", "ewidencja_cp", "ecp"],
    "P2": ["karta_urlopowa", "karty_urlopowe"],
    "P3": ["lista_obecnosci", "obecnosc"],
    "P4": ["lista_plac", "lista_wynagrodzen", "lp"],
    "P5": ["wyplata_rak", "rece_wlasne", "rak_wlasnych"],
    "P6": ["odziez_robocza", "ekwiwalent_odziez", "bhp_odziez"],
    "P7": ["zasilki", "dokumentacja_zasilkowa", "l4", "zwolnienie_lekarskie"],
    "P8": ["karta_przychodow", "przychody", "karta_zarobkow"],
    "P9": ["zus_zua", "zua"],
    "P10": ["zus_zwua", "zwua", "wyrejestrowanie"],
    "P11": ["zus_zcna", "zcna"],
}

# Pełna lista dokumentów dla promptu AI
DOCUMENT_LIST_FOR_PROMPT = """
LISTA DOKUMENTÓW KADROWYCH (ID – nazwa):
A1  – Kwestionariusz osobowy kandydata
A2  – CV / życiorys zawodowy
A3  – List motywacyjny
A4  – Dokumenty potwierdzające kwalifikacje (dyplomy, certyfikaty, świadectwa szkolne)
A5  – Skierowanie na badania wstępne
A6  – Orzeczenie lekarskie dopuszczające do pracy
B1  – Kwestionariusz osoby zatrudnionej
B2  – Zgoda na przetwarzanie danych osobowych (RODO / klauzula)
B3  – Umowa o pracę
B4  – Informacja o warunkach zatrudnienia (art. 29 KP)
B5  – Zakres obowiązków / czynności pracownika
B6  – Szkolenie BHP – karta szkolenia / potwierdzenie odbycia
B7  – PIT-2 / oświadczenie podatkowe
B8  – Informacja dot. równego traktowania w zatrudnieniu
B9  – Oświadczenie KUP (koszty uzyskania przychodu)
B10 – Oświadczenie FP (Fundusz Pracy)
B11 – Potwierdzenie zapoznania z regulaminem pracy
B12 – Oświadczenie o sposobie wypłaty wynagrodzenia (przelew / gotówka)
B13 – Oświadczenie opieka K.P. art. 188 (opieka nad dzieckiem)
B14 – Dokumenty dot. powierzenia mienia pracownikowi
B15 – Obwieszczenie o systemie i rozkładzie czasu pracy
B16 – Wniosek o zgłoszenie członka rodziny do ubezpieczenia zdrowotnego
B17 – Oświadczenie o zapoznaniu się z obwieszczeniem o czasie pracy
B18 – Deklaracja PPK (Pracownicze Plany Kapitałowe)
B19 – Aneks / aneksy do umowy o pracę
B20 – Zajęcie wierzytelności / pismo komornicze
B21 – Wnioski urlopowe
C1  – Rozwiązanie umowy o pracę / wypowiedzenie
C2  – Potwierdzenie odbioru świadectwa pracy
C3  – Wniosek o sprostowanie świadectwa pracy
C4  – Rozliczenie ekwiwalentu za urlop
D1  – Odpis zawiadomienia o ukaraniu karą porządkową (upomnienie / nagana)
D2  – Wyjaśnienia pracownika w sprawie kary porządkowej
D3  – Informacja o usunięciu kary z akt pracowniczych
E1  – Protokół z kontroli trzeźwości / substancji psychoaktywnych
E2  – Wyniki badania trzeźwości
E3  – Uzasadnienie przeprowadzenia kontroli trzeźwości
P1  – Ewidencja czasu pracy
P2  – Karty urlopowe
P3  – Lista obecności
P4  – Lista płac / lista wynagrodzeń
P5  – Wnioski o wypłatę wynagrodzenia do rąk własnych
P6  – Dokumentacja odzieży roboczej / ekwiwalentów BHP
P7  – Dokumentacja zasiłkowa (ZUS, L4, zwolnienia lekarskie)
P8  – Karty przychodów zatrudnionych
P9  – ZUS ZUA (zgłoszenie pracownika do ubezpieczeń)
P10 – ZUS ZWUA (wyrejestrowanie pracownika z ubezpieczeń)
P11 – ZUS ZCNA (zgłoszenie członka rodziny do ubezpieczenia zdrowotnego)
"""

SYSTEM_PROMPT = f"""Jesteś ekspertem kadrowo-płacowym specjalizującym się w dokumentacji pracowniczej polskich firm.
Otrzymujesz fragment górnej części dokumentu kadrowego (nagłówek, ok. 20% strony).
Twoim zadaniem jest zidentyfikowanie, który dokument z listy to jest.

{DOCUMENT_LIST_FOR_PROMPT}

ZASADY:
- Patrz głównie na nagłówek, tytuł, pierwsze zdania dokumentu
- Ignoruj dane osobowe (nazwiska, numery PESEL, daty itp.)
- Jeśli widzisz wyraźny tytuł pasujący do listy → status PEWNY
- Jeśli masz wątpliwości (nieczytelny skan, brak tytułu, wiele możliwości) → status WĄTPLIWY
- Jeśli dokument zupełnie nie pasuje do żadnej pozycji → document_id: null, status WĄTPLIWY

Odpowiedz WYŁĄCZNIE poprawnym JSON-em (bez markdown, bez komentarzy):
{{"document_id": "B3", "status": "PEWNY", "reason": "Nagłówek zawiera tytuł Umowa o pracę"}}
"""


# ─────────────────────────────────────────────
#  FUNKCJE POMOCNICZE
# ─────────────────────────────────────────────

def match_filename(filename: str) -> str | None:
    """
    Próbuje dopasować nazwę pliku do ID dokumentu na podstawie słownika wzorców.
    Zwraca ID lub None jeśli brak pewnego dopasowania.
    """
    name = filename.lower()
    # Usuń rozszerzenie i zamień separatory
    name = re.sub(r'\.(pdf|png|jpg|jpeg)$', '', name)
    name = name.replace('-', '_').replace(' ', '_')

    # Szukaj wzorców
    matches = []
    for doc_id, patterns in FILENAME_PATTERNS.items():
        for pattern in patterns:
            if pattern in name:
                matches.append(doc_id)
                break

    # Pewne dopasowanie tylko jeśli jeden wynik
    if len(matches) == 1:
        return matches[0]
    return None


def get_page_crop_png(pdf_bytes: bytes, page_idx: int = 0, crop_ratio: float = 0.22) -> bytes:
    """
    Wycina górne crop_ratio% strony PDF i zwraca PNG jako bytes.
    Nie wysyła danych osobowych — tylko nagłówek/tytuł dokumentu.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_idx >= len(doc):
        page_idx = 0
    page = doc[page_idx]
    rect = page.rect
    clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * crop_ratio)
    mat = fitz.Matrix(2.0, 2.0)  # 2x zoom dla lepszej czytelności
    pixmap = page.get_pixmap(matrix=mat, clip=clip)
    doc.close()
    return pixmap.tobytes("png")


def count_pdf_pages(pdf_bytes: bytes) -> int:
    """Zwraca liczbę stron PDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(doc)
    doc.close()
    return n


def analyze_page_with_ai(
    image_png: bytes,
    filename: str,
    filename_hint: str | None,
    client: anthropic.Anthropic,
) -> dict:
    """
    Wysyła crop nagłówka do Claude API i zwraca wynik klasyfikacji.
    
    Zwraca dict: {
        "document_id": str | None,
        "status": "PEWNY" | "WĄTPLIWY",
        "reason": str,
        "source": "AI" | "FILENAME+AI"
    }
    """
    b64 = base64.standard_b64encode(image_png).decode()

    hint_text = ""
    if filename_hint:
        hint_text = f"\nWskazówka z nazwy pliku: plik może być dokumentem {filename_hint} ({QUESTION_MAP.get(filename_hint, {}).get('text', '')}). Potwierdź lub zaprzecz na podstawie treści."

    user_message = f"Nazwa pliku: {filename}{hint_text}\n\nZidentyfikuj ten dokument kadrowy."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": user_message},
                    ],
                }
            ],
        )

        raw = response.content[0].text.strip()
        # Usuń ewentualne markdown fences
        raw = re.sub(r"```json|```", "", raw).strip()
        result = json.loads(raw)

        source = "FILENAME+AI" if filename_hint and result.get("document_id") == filename_hint else "AI"
        return {
            "document_id": result.get("document_id"),
            "status": result.get("status", "WĄTPLIWY"),
            "reason": result.get("reason", "Brak uzasadnienia"),
            "source": source,
        }

    except Exception as e:
        return {
            "document_id": filename_hint,
            "status": "WĄTPLIWY",
            "reason": f"Błąd analizy AI: {str(e)[:100]}",
            "source": "ERROR",
        }


# ─────────────────────────────────────────────
#  GŁÓWNA FUNKCJA ANALIZY
# ─────────────────────────────────────────────

def analyze_uploaded_files(
    uploaded_files: list,
    api_key: str,
    progress_callback=None,
) -> list[dict]:
    """
    Analizuje listę wgranych plików PDF.
    
    Każdy wynik: {
        "filename": str,
        "page": int,          # numer strony (0-based), dla 1-stronicowych = 0
        "document_id": str | None,
        "status": "PEWNY" | "WĄTPLIWY",
        "reason": str,
        "source": str,
        "image_png": bytes,   # crop nagłówka do podglądu
    }
    """
    client = anthropic.Anthropic(api_key=api_key)
    results = []

    # Rozwiń wielostronicowe PDF-y na strony
    tasks = []  # lista (filename_display, pdf_bytes, page_idx)
    for uf in uploaded_files:
        pdf_bytes = uf.read()
        n_pages = count_pdf_pages(pdf_bytes)
        if n_pages == 1:
            tasks.append((uf.name, pdf_bytes, 0))
        else:
            for i in range(n_pages):
                tasks.append((f"{uf.name} (str. {i+1})", pdf_bytes, i))

    total = len(tasks)

    for idx, (filename_display, pdf_bytes, page_idx) in enumerate(tasks):
        if progress_callback:
            progress_callback(idx, total, filename_display)

        # Etap 1: dopasowanie nazwy pliku
        base_name = filename_display.split(" (str.")[0]  # usuń suffix strony
        filename_hint = match_filename(base_name)

        # Etap 2: crop nagłówka
        try:
            image_png = get_page_crop_png(pdf_bytes, page_idx)
        except Exception as e:
            results.append({
                "filename": filename_display,
                "page": page_idx,
                "document_id": filename_hint,
                "status": "WĄTPLIWY",
                "reason": f"Błąd odczytu PDF: {str(e)[:80]}",
                "source": "ERROR",
                "image_png": None,
            })
            continue

        # Etap 3: analiza AI
        ai_result = analyze_page_with_ai(image_png, filename_display, filename_hint, client)

        results.append({
            "filename": filename_display,
            "page": page_idx,
            "document_id": ai_result["document_id"],
            "status": ai_result["status"],
            "reason": ai_result["reason"],
            "source": ai_result["source"],
            "image_png": image_png,
        })

    if progress_callback:
        progress_callback(total, total, "Analiza zakończona")

    return results


def results_to_answers(confirmed_results: list[dict]) -> dict:
    """
    Konwertuje potwierdzone wyniki analizy na słownik odpowiedzi formularza.
    Dokumenty PEWNE i potwierdzone przez użytkownika → TAK
    Pozostałe → NIE (domyślna odpowiedź z config)
    """
    from config import ANS, QUESTION_MAP

    # Domyślnie wszystkie pytania → pierwsza opcja (zazwyczaj TAK lub pierwsza)
    answers = {}
    for q_id, q in QUESTION_MAP.items():
        ans_type = q.get("ans", "tak_nie")
        opts = ANS.get(ans_type, ["TAK", "NIE"])
        # Dla tak_nie: domyślnie NIE (brak dokumentu)
        answers[q_id] = "NIE" if "NIE" in opts else opts[-1]

    # Zaznacz potwierdzone dokumenty jako TAK / pierwsza pozytywna opcja
    for r in confirmed_results:
        doc_id = r.get("document_id")
        if not doc_id or doc_id not in QUESTION_MAP:
            continue
        q = QUESTION_MAP[doc_id]
        ans_type = q.get("ans", "tak_nie")
        opts = ANS.get(ans_type, ["TAK", "NIE"])
        # Dla tak_nie/tak_nie_nd → TAK
        # Dla złożonych → pierwsza opcja (zazwyczaj pozytywna)
        answers[doc_id] = opts[0]

    return answers
