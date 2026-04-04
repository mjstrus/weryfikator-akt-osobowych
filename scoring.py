# scoring.py – Logika oceny i kalkulacji braków

from config import SECTIONS, QUESTION_MAP, ANS


def get_gap_status(q_id: str, answer) -> str:
    """
    Zwraca: 'ok', 'brak', 'nd', 'wymaga_weryfikacji'
    """
    if answer is None or answer == "" or answer == "—":
        return "brak"

    q = QUESTION_MAP.get(q_id, {})
    ans_type = q.get("ans", "tak_nie")

    if ans_type == "tak_nie":
        return "ok" if answer == "TAK" else "brak"

    elif ans_type == "tak_nie_nd":
        if answer == "TAK":
            return "ok"
        elif answer == "ND":
            return "nd"
        return "brak"

    elif ans_type == "lp_5":
        if answer in ("Jest oświadczenie i jest stosowane", "Zweryfikowano z listą płac"):
            return "ok"
        elif answer in (
            "Jest oświadczenie i nie jest stosowane",
            "Nie ma oświadczenia i jest stosowane",
        ):
            return "wymaga_weryfikacji"
        return "brak"

    elif ans_type == "wyplata_3":
        return "ok" if answer in ("TAK", "Zweryfikowano z listą płac") else "brak"

    elif ans_type == "wyplata_4":
        if answer == "Jest oświadczenie i jest stosowane":
            return "ok"
        elif answer in (
            "Jest oświadczenie i nie jest stosowane",
            "Nie ma oświadczenia i jest stosowane",
        ):
            return "wymaga_weryfikacji"
        return "brak"

    elif ans_type == "aneksy":
        return (
            "ok"
            if answer in ("Nie było aneksów", "Były aneksy i są w aktach", "Zweryfikowano z listą płac")
            else "brak"
        )

    elif ans_type == "wnioski_url":
        return "ok" if answer in ("Tak", "Nie, ale urlop nie był wykorzystywany") else "brak"

    elif ans_type == "ekwiwalent":
        return "ok" if answer in ("Jest wniosek i wypłacono", "Nie ma wniosku, bo nie należał się") else "brak"

    return "ok"


def get_applicable_questions(status: str, wymiar: str, answers: dict) -> list[dict]:
    """
    Zwraca listę pytań mających zastosowanie w danym audycie.
    """
    applicable = []
    for section in SECTIONS:
        # Czy sekcja dotyczy danego statusu pracownika?
        if status not in section.get("applies_to", []):
            continue

        for q in section["questions"]:
            # Czy pytanie dotyczy danego statusu?
            q_applies = q.get("applies_to_status", section.get("applies_to", ["aktualny", "były"]))
            if status not in q_applies:
                continue

            # Logika warunkowa
            condition = q.get("condition")
            if condition:
                if condition == "B10_fp" and wymiar == "Pełny etat":
                    continue
                elif condition == "D1_not_nd" and answers.get("D1") == "ND":
                    continue
                elif condition == "E1_not_nd" and answers.get("E1") == "ND":
                    continue
                elif condition == "P11_zcna" and answers.get("B16") != "TAK":
                    continue

            # Dodaj section_id do pytania jeśli go brak
            q_with_section = {**q, "section_id": section["id"]}
            applicable.append(q_with_section)

    return applicable


def calculate_scores(answers: dict, status: str, wymiar: str) -> dict:
    """
    Oblicza braki, kompletność i poziom ryzyka.
    """
    applicable = get_applicable_questions(status, wymiar, answers)

    obligatory_total = 0
    obligatory_gaps = 0
    conditional_total = 0
    conditional_gaps = 0
    voluntary_total = 0
    voluntary_gaps = 0

    gap_list = []

    for q in applicable:
        q_id = q["id"]
        q_status = q.get("status", "obowiązkowe")
        answer = answers.get(q_id)
        gs = get_gap_status(q_id, answer)

        # ND = nie dotyczy – pomijamy w statystykach
        if gs == "nd":
            continue

        if q_status == "obowiązkowe":
            obligatory_total += 1
            if gs in ("brak", "wymaga_weryfikacji"):
                obligatory_gaps += 1
                gap_list.append(
                    {
                        "id": q_id,
                        "section": q["section_id"],
                        "text": q["text"],
                        "status": q_status,
                        "gap_status": gs,
                        "answer": answer or "—",
                        "recommendation": "Wymaga niezwłocznej reakcji",
                    }
                )

        elif q_status == "warunkowe":
            conditional_total += 1
            if gs in ("brak", "wymaga_weryfikacji"):
                conditional_gaps += 1
                gap_list.append(
                    {
                        "id": q_id,
                        "section": q["section_id"],
                        "text": q["text"],
                        "status": q_status,
                        "gap_status": gs,
                        "answer": answer or "—",
                        "recommendation": "Wymaga niezwłocznej reakcji",
                    }
                )

        elif q_status == "dobrowolne":
            voluntary_total += 1
            if gs in ("brak", "wymaga_weryfikacji"):
                voluntary_gaps += 1
                gap_list.append(
                    {
                        "id": q_id,
                        "section": q["section_id"],
                        "text": q["text"],
                        "status": q_status,
                        "gap_status": gs,
                        "answer": answer or "—",
                        "recommendation": "Uzupełnić w terminie 14 dni",
                    }
                )

    # Poziom ryzyka na podstawie % braków obowiązkowych
    if obligatory_total == 0:
        risk_pct = 0.0
        risk_level = "niskie"
    else:
        risk_pct = (obligatory_gaps / obligatory_total) * 100
        if risk_pct <= 15:
            risk_level = "niskie"
        elif risk_pct <= 40:
            risk_level = "średnie"
        else:
            risk_level = "wysokie"

    # Kompletność: 1 - (łączne braki / łącznie pytań mających zastosowanie)
    total_applicable = obligatory_total + conditional_total + voluntary_total
    total_gaps = obligatory_gaps + conditional_gaps + voluntary_gaps
    completeness = round((1 - total_gaps / total_applicable) * 100, 1) if total_applicable > 0 else 100.0

    return {
        "obligatory_total": obligatory_total,
        "obligatory_gaps": obligatory_gaps,
        "conditional_total": conditional_total,
        "conditional_gaps": conditional_gaps,
        "voluntary_total": voluntary_total,
        "voluntary_gaps": voluntary_gaps,
        "risk_pct": round(risk_pct, 1),
        "risk_level": risk_level,
        "completeness": completeness,
        "gap_list": gap_list,
    }


RISK_COLORS = {
    "niskie": "#27ae60",
    "średnie": "#f39c12",
    "wysokie": "#e74c3c",
}

RISK_EMOJI = {
    "niskie": "🟢",
    "średnie": "🟡",
    "wysokie": "🔴",
}
