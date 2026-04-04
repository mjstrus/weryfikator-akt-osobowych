# config.py – Konfiguracja formularza audytowego

ABACUS = {
    "nazwa": "Abacus Centrum Księgowe sp. z o.o.",
    "adres": "ul. Zielona 13 lok 3, 24-100 Puławy",
    "www": "www.abacus24.pl",
    "email": "biuro@abacus24.pl",
    "tel": "500 120 075",
}

WYMIAR_ETATU_OPTIONS = [
    "Pełny etat",
    "3/4 etatu",
    "1/2 etatu",
    "1/4 etatu",
    "Inny",
]

STATUS_OPTIONS = ["aktualny", "były"]

# Typy odpowiedzi
ANS = {
    "tak_nie": ["TAK", "NIE"],
    "tak_nie_nd": ["TAK", "NIE", "ND"],
    "lp_5": [
        "Jest oświadczenie i jest stosowane",
        "Jest oświadczenie i nie jest stosowane",
        "Nie ma oświadczenia i jest stosowane",
        "Nie ma oświadczenia i nie jest stosowane",
        "Zweryfikowano z listą płac",
    ],
    "wyplata_3": ["TAK", "NIE", "Zweryfikowano z listą płac"],
    "wyplata_4": [
        "Jest oświadczenie i jest stosowane",
        "Jest oświadczenie i nie jest stosowane",
        "Nie ma oświadczenia i jest stosowane",
        "Nie ma oświadczenia i nie jest stosowane",
    ],
    "aneksy": [
        "Nie było aneksów",
        "Były aneksy, ale nie ma w aktach",
        "Były aneksy i są w aktach",
        "Zweryfikowano z listą płac",
    ],
    "wnioski_url": [
        "Tak",
        "Nie, ale urlop był wykorzystywany",
        "Nie, ale urlop nie był wykorzystywany",
    ],
    "ekwiwalent": [
        "Jest wniosek i wypłacono",
        "Nie ma wniosku, ale wypłacono",
        "Nie ma wniosku, bo nie należał się",
    ],
}

SECTIONS = [
    {
        "id": "A",
        "title": "Część A – Dokumenty rekrutacyjne",
        "desc": "Dokumenty zgromadzone na etapie rekrutacji pracownika.",
        "applies_to": ["aktualny"],
        "questions": [
            {
                "id": "A1",
                "text": "Kwestionariusz osobowy kandydata",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "A2",
                "text": "CV (jeśli zostało załączone)",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "A3",
                "text": "List motywacyjny (jeśli został załączony)",
                "ans": "tak_nie",
                "status": "dobrowolne",
            },
            {
                "id": "A4",
                "text": "Dokumenty potwierdzające kwalifikacje",
                "ans": "tak_nie",
                "status": "warunkowe",
                "uwaga": "Brak dokumentów kwalifikacji może wpływać na wymiar urlopu – pozycja wymaga analizy.",
            },
            {
                "id": "A5",
                "text": "Skierowanie na badania wstępne",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "A6",
                "text": "Orzeczenie lekarskie dopuszczające do pracy",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
        ],
    },
    {
        "id": "B",
        "title": "Część B – Dokumenty dotyczące zatrudnienia",
        "desc": "Dokumenty zgromadzone w trakcie nawiązania i trwania stosunku pracy.",
        "applies_to": ["aktualny"],
        "questions": [
            {
                "id": "B1",
                "text": "Kwestionariusz osoby zatrudnionej",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B2",
                "text": "Zgoda na przetwarzanie danych osobowych (RODO)",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B3",
                "text": "Umowa o pracę",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B4",
                "text": "Informacja o warunkach zatrudnienia",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B5",
                "text": "Zakres obowiązków",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B6",
                "text": "Szkolenie BHP – potwierdzenie odbycia",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B7",
                "text": "PIT-2",
                "ans": "lp_5",
                "status": "dobrowolne",
                "lp_note": True,
            },
            {
                "id": "B8",
                "text": "Informacja dot. równego traktowania",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B9",
                "text": "Oświadczenie KUP (koszty uzyskania przychodu)",
                "ans": "lp_5",
                "status": "dobrowolne",
                "lp_note": True,
            },
            {
                "id": "B10",
                "text": "Oświadczenie FP (Fundusz Pracy)",
                "ans": "lp_5",
                "status": "warunkowe",
                "lp_note": True,
                "condition": "B10_fp",  # ukryj jeśli pełny etat
            },
            {
                "id": "B11",
                "text": "Potwierdzenie zapoznania z regulaminem pracy",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B12",
                "text": "Oświadczenie o sposobie wypłaty wynagrodzenia",
                "ans": "wyplata_3",
                "status": "obowiązkowe",
                "lp_note": True,
            },
            {
                "id": "B13",
                "text": "Oświadczenie – opieka (K.P. art. 188)",
                "ans": "tak_nie_nd",
                "status": "warunkowe",
            },
            {
                "id": "B14",
                "text": "Dokumenty dot. powierzenia mienia",
                "ans": "tak_nie_nd",
                "status": "warunkowe",
            },
            {
                "id": "B15",
                "text": "Obwieszczenie o systemie i rozkładzie czasu pracy",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B16",
                "text": "Wniosek o zgłoszenie członka rodziny do ubezpieczenia zdrowotnego",
                "ans": "tak_nie",
                "status": "dobrowolne",
            },
            {
                "id": "B17",
                "text": "Oświadczenie o zapoznaniu się z obwieszczeniem",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "B18",
                "text": "Deklaracja PPK",
                "ans": "lp_5",
                "status": "warunkowe",
                "lp_note": True,
            },
            {
                "id": "B19",
                "text": "Aneksy do umowy o pracę",
                "ans": "aneksy",
                "status": "obowiązkowe",
                "lp_note": True,
            },
            {
                "id": "B20",
                "text": "Zajęcie wierzytelności (komornicze)",
                "ans": "tak_nie_nd",
                "status": "warunkowe",
            },
            {
                "id": "B21",
                "text": "Wnioski urlopowe",
                "ans": "wnioski_url",
                "status": "obowiązkowe",
            },
        ],
    },
    {
        "id": "C",
        "title": "Część C – Dokumenty ustania zatrudnienia",
        "desc": "Dokumenty dotyczące zakończenia stosunku pracy.",
        "applies_to": ["były"],
        "questions": [
            {
                "id": "C1",
                "text": "Rozwiązanie umowy o pracę",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "C2",
                "text": "Potwierdzenie odbioru świadectwa pracy",
                "ans": "tak_nie",
                "status": "obowiązkowe",
            },
            {
                "id": "C3",
                "text": "Wniosek o sprostowanie świadectwa pracy",
                "ans": "tak_nie_nd",
                "status": "obowiązkowe",
            },
            {
                "id": "C4",
                "text": "Rozliczenie ekwiwalentu za urlop",
                "ans": "ekwiwalent",
                "status": "obowiązkowe",
            },
        ],
    },
    {
        "id": "D",
        "title": "Część D – Dokumentacja kar porządkowych",
        "desc": "Dokumenty dotyczące nałożonych kar porządkowych.",
        "applies_to": ["aktualny"],
        "questions": [
            {
                "id": "D1",
                "text": "Odpis zawiadomienia o ukaraniu",
                "ans": "tak_nie_nd",
                "status": "warunkowe",
            },
            {
                "id": "D2",
                "text": "Wyjaśnienia pracownika",
                "ans": "tak_nie",
                "status": "warunkowe",
                "condition": "D1_not_nd",
            },
            {
                "id": "D3",
                "text": "Informacja o usunięciu kary z akt",
                "ans": "tak_nie",
                "status": "warunkowe",
                "condition": "D1_not_nd",
            },
        ],
    },
    {
        "id": "E",
        "title": "Część E – Dokumenty dot. kontroli trzeźwości",
        "desc": "Dokumenty dotyczące przeprowadzonych kontroli trzeźwości lub substancji psychoaktywnych.",
        "applies_to": ["aktualny"],
        "questions": [
            {
                "id": "E1",
                "text": "Protokół z kontroli trzeźwości / substancji psychoaktywnych",
                "ans": "tak_nie_nd",
                "status": "warunkowe",
            },
            {
                "id": "E2",
                "text": "Wyniki badania trzeźwości",
                "ans": "tak_nie",
                "status": "warunkowe",
                "condition": "E1_not_nd",
            },
            {
                "id": "E3",
                "text": "Uzasadnienie przeprowadzenia kontroli",
                "ans": "tak_nie",
                "status": "warunkowe",
                "condition": "E1_not_nd",
            },
        ],
    },
    {
        "id": "P",
        "title": "Dokumentacja Pozaaktowa",
        "desc": "Dokumenty przechowywane poza teczką akt osobowych pracownika.",
        "applies_to": ["aktualny", "były"],
        "questions": [
            {
                "id": "P1",
                "text": "Ewidencja czasu pracy",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
                "extra_comment": True,
            },
            {
                "id": "P2",
                "text": "Karty urlopowe",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P3",
                "text": "Listy obecności",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P4",
                "text": "Lista płac",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P5",
                "text": "Wnioski o wypłatę wynagrodzenia do rąk własnych",
                "ans": "wyplata_4",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P6",
                "text": "Dokumentacja odzieży roboczej / ekwiwalentów",
                "ans": "tak_nie_nd",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P7",
                "text": "Dokumentacja zasiłkowa (ZUS, L4 itp.)",
                "ans": "tak_nie_nd",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P8",
                "text": "Karty przychodów zatrudnionych",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P9",
                "text": "ZUS ZUA (zgłoszenie do ubezpieczeń)",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["aktualny"],
            },
            {
                "id": "P10",
                "text": "ZUS ZWUA (wyrejestrowanie z ubezpieczeń)",
                "ans": "tak_nie",
                "status": "obowiązkowe",
                "applies_to_status": ["były"],
            },
            {
                "id": "P11",
                "text": "ZUS ZCNA (zgłoszenie członka rodziny)",
                "ans": "tak_nie",
                "status": "dobrowolne",
                "applies_to_status": ["aktualny"],
                "condition": "P11_zcna",  # only if B16 == TAK
            },
        ],
    },
]

# Flat lookup map
QUESTION_MAP = {}
for _sec in SECTIONS:
    for _q in _sec["questions"]:
        QUESTION_MAP[_q["id"]] = {**_q, "section_id": _sec["id"]}

LEGAL_CONSEQUENCES = """
**Możliwe konsekwencje prawne przy kontroli PIP / ZUS:**

• **Brak dokumentów obowiązkowych** (umowa, badania lekarskie, szkolenie BHP, kwestionariusze):
  Inspektor PIP może nałożyć mandat karny od 1.000 do 30.000 zł za naruszenie przepisów Kodeksu pracy
  (art. 281 § 1 K.p. i nast.).

• **Brak dokumentacji ZUS** (ZUA, ZWUA):
  ZUS może nałożyć karę grzywny do 5.000 zł, a przy powtarzających się naruszeniach wszcząć postępowanie
  wyjaśniające i naliczyć zaległe składki z odsetkami.

• **Brak orzeczenia lekarskiego / skierowania na badania**:
  Dopuszczenie do pracy bez ważnych badań profilaktycznych stanowi wykroczenie z art. 283 § 1 K.p.

• **Brak oświadczenia o warunkach zatrudnienia** (art. 29 § 3 K.p.):
  Naruszenie skutkuje mandatem PIP oraz możliwością roszczeń odszkodowawczych pracownika.

• **Brak dokumentacji urlopowej i ewidencji czasu pracy**:
  Możliwe roszczenia pracownika o zaległe urlopy i nadgodziny. PIP może nakazać uzupełnienie dokumentacji.

Powyższe informacje mają charakter orientacyjny. W celu oceny konkretnej sytuacji prawnej skonsultuj się
z radcą prawnym lub adwokatem specjalizującym się w prawie pracy.
"""
