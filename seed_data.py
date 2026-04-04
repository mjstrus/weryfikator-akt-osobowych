#!/usr/bin/env python3
# seed_data.py – Przykładowe dane testowe

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import db
from scoring import calculate_scores

SEED_AUDYTY = [
    # 1. Pracownik aktualny – kompletna dokumentacja (niskie ryzyko)
    {
        "firma": "XYZ Production sp. z o.o.",
        "imie": "Anna",
        "nazwisko": "Kowalska",
        "stanowisko": "Główna Księgowa",
        "data_zatrudnienia": "01.03.2020",
        "pesel": "85030112345",
        "status_pracownika": "aktualny",
        "wymiar_etatu": "Pełny etat",
        "minimalne_wynagrodzenie": "TAK",
        "answers": {
            "A1": "TAK", "A2": "TAK", "A3": "TAK", "A4": "TAK", "A5": "TAK", "A6": "TAK",
            "B1": "TAK", "B2": "TAK", "B3": "TAK", "B4": "TAK", "B5": "TAK", "B6": "TAK",
            "B7": "Jest oświadczenie i jest stosowane",
            "B8": "TAK",
            "B9": "Jest oświadczenie i jest stosowane",
            "B10": "NIE",  # pełny etat – pyt. niewidoczne
            "B11": "TAK", "B12": "TAK", "B13": "TAK", "B14": "ND", "B15": "TAK",
            "B16": "NIE", "B17": "TAK",
            "B18": "Zweryfikowano z listą płac",
            "B19": "Nie było aneksów",
            "B20": "ND", "B21": "Tak",
            "D1": "ND", "D2": "TAK", "D3": "TAK",
            "E1": "ND", "E2": "TAK", "E3": "TAK",
            "P1": "TAK", "P2": "TAK", "P3": "TAK", "P4": "TAK",
            "P5": "Jest oświadczenie i jest stosowane",
            "P6": "ND", "P7": "TAK", "P8": "TAK", "P9": "TAK",
            "P10": "NIE", "P11": "NIE",
        },
        "data_weryfikacji": "04.04.2026",
        "weryfikujacy_imie_nazwisko": "Marcin Strusiński",
        "weryfikujacy_stanowisko": "Specjalista ds. kadr",
    },
    # 2. Pracownik aktualny – braki obowiązkowe (wysokie ryzyko)
    {
        "firma": "XYZ Production sp. z o.o.",
        "imie": "Tomasz",
        "nazwisko": "Nowak",
        "stanowisko": "Magazynier",
        "data_zatrudnienia": "15.06.2023",
        "pesel": "90061567890",
        "status_pracownika": "aktualny",
        "wymiar_etatu": "Pełny etat",
        "minimalne_wynagrodzenie": "TAK",
        "answers": {
            "A1": "TAK", "A2": "NIE", "A3": "NIE", "A4": "NIE", "A5": "NIE", "A6": "NIE",
            "B1": "TAK", "B2": "NIE", "B3": "TAK", "B4": "NIE", "B5": "NIE", "B6": "NIE",
            "B7": "Nie ma oświadczenia i nie jest stosowane",
            "B8": "NIE",
            "B9": "Nie ma oświadczenia i nie jest stosowane",
            "B10": "NIE",
            "B11": "NIE", "B12": "NIE", "B13": "ND", "B14": "ND", "B15": "NIE",
            "B16": "NIE", "B17": "NIE",
            "B18": "Nie ma oświadczenia i nie jest stosowane",
            "B19": "Nie było aneksów",
            "B20": "ND",
            "B21": "Nie, ale urlop był wykorzystywany",
            "D1": "ND", "D2": "NIE", "D3": "NIE",
            "E1": "ND", "E2": "NIE", "E3": "NIE",
            "P1": "NIE", "P2": "NIE", "P3": "TAK", "P4": "TAK",
            "P5": "Nie ma oświadczenia i nie jest stosowane",
            "P6": "ND", "P7": "ND", "P8": "NIE", "P9": "TAK",
            "P10": "NIE", "P11": "NIE",
        },
        "data_weryfikacji": "04.04.2026",
        "weryfikujacy_imie_nazwisko": "Marcin Strusiński",
        "weryfikujacy_stanowisko": "Specjalista ds. kadr",
    },
    # 3. Pracownik aktualny – 1/2 etatu, braki warunkowe (średnie ryzyko)
    {
        "firma": "ABC Usługi s.c.",
        "imie": "Katarzyna",
        "nazwisko": "Wiśniewska",
        "stanowisko": "Specjalista ds. obsługi klienta",
        "data_zatrudnienia": "01.09.2022",
        "pesel": "95091523456",
        "status_pracownika": "aktualny",
        "wymiar_etatu": "1/2 etatu",
        "minimalne_wynagrodzenie": "NIE",
        "answers": {
            "A1": "TAK", "A2": "TAK", "A3": "NIE", "A4": "TAK", "A5": "TAK", "A6": "TAK",
            "B1": "TAK", "B2": "TAK", "B3": "TAK", "B4": "TAK", "B5": "TAK", "B6": "TAK",
            "B7": "Jest oświadczenie i jest stosowane",
            "B8": "TAK",
            "B9": "Jest oświadczenie i nie jest stosowane",
            "B10": "Nie ma oświadczenia i nie jest stosowane",
            "B11": "TAK", "B12": "TAK", "B13": "ND", "B14": "ND", "B15": "TAK",
            "B16": "TAK", "B17": "TAK",
            "B18": "Zweryfikowano z listą płac",
            "B19": "Były aneksy i są w aktach",
            "B20": "ND",
            "B21": "Tak",
            "D1": "TAK", "D2": "NIE", "D3": "NIE",
            "E1": "ND", "E2": "TAK", "E3": "TAK",
            "P1": "TAK", "P2": "TAK", "P3": "TAK", "P4": "TAK",
            "P5": "Jest oświadczenie i jest stosowane",
            "P6": "ND", "P7": "ND", "P8": "TAK", "P9": "TAK",
            "P10": "NIE",
            "P11": "TAK",
        },
        "data_weryfikacji": "04.04.2026",
        "weryfikujacy_imie_nazwisko": "Marcin Strusiński",
        "weryfikujacy_stanowisko": "Specjalista ds. kadr",
    },
    # 4. Pracownik były – kompletna dokumentacja
    {
        "firma": "ABC Usługi s.c.",
        "imie": "Piotr",
        "nazwisko": "Zielański",
        "stanowisko": "Kierownik Projektu",
        "data_zatrudnienia": "15.01.2019",
        "pesel": "82011534567",
        "status_pracownika": "były",
        "wymiar_etatu": None,
        "minimalne_wynagrodzenie": None,
        "answers": {
            "C1": "TAK", "C2": "TAK", "C3": "ND", "C4": "Jest wniosek i wypłacono",
            "P10": "TAK",
        },
        "data_weryfikacji": "04.04.2026",
        "weryfikujacy_imie_nazwisko": "Marcin Strusiński",
        "weryfikujacy_stanowisko": "Specjalista ds. kadr",
    },
    # 5. Pracownik były – braki (wysokie ryzyko)
    {
        "firma": "XYZ Production sp. z o.o.",
        "imie": "Marta",
        "nazwisko": "Jabłońska",
        "stanowisko": "Asystentka",
        "data_zatrudnienia": "01.07.2021",
        "pesel": "93070245678",
        "status_pracownika": "były",
        "wymiar_etatu": None,
        "minimalne_wynagrodzenie": None,
        "answers": {
            "C1": "NIE", "C2": "NIE", "C3": "ND",
            "C4": "Nie ma wniosku, ale wypłacono",
            "P10": "NIE",
        },
        "data_weryfikacji": "04.04.2026",
        "weryfikujacy_imie_nazwisko": "Marcin Strusiński",
        "weryfikujacy_stanowisko": "Specjalista ds. kadr",
    },
]


def seed():
    existing = db.get_all_audyty()
    if existing:
        print(f"Baza zawiera już {len(existing)} audytów. Pomijam wczytywanie danych testowych.")
        print("Aby załadować dane testowe od nowa, usuń plik audyty.db i uruchom ponownie.")
        return

    print("Wczytywanie przykładowych danych testowych...")
    for i, s in enumerate(SEED_AUDYTY, 1):
        answers = s.pop("answers")
        status = s["status_pracownika"]
        wymiar = s.get("wymiar_etatu") or "Pełny etat"

        scores = calculate_scores(answers, status, wymiar)

        record = {
            **s,
            "odpowiedzi": answers,
            "braki_obowiazkowe": scores["obligatory_gaps"],
            "braki_warunkowe": scores["conditional_gaps"],
            "braki_dobrowolne": scores["voluntary_gaps"],
            "kompletnosc_procent": scores["completeness"],
            "poziom_ryzyka": scores["risk_level"],
            "gap_list": scores["gap_list"],
        }
        new_id = db.save_audyt(record)
        print(
            f"  [{i}] {record['imie']} {record['nazwisko']} ({record['firma']}) "
            f"→ ID {new_id} | ryzyko: {scores['risk_level']} | kompletność: {scores['completeness']}%"
        )

    print(f"\n✅ Wczytano {len(SEED_AUDYTY)} przykładowych audytów.")
    print("Uruchom aplikację: python -m streamlit run app.py")


if __name__ == "__main__":
    seed()
