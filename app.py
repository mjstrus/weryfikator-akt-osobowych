# app.py – Aplikacja Streamlit: Audyt Akt Osobowych
# Abacus Centrum Księgowe sp. z o.o.

import streamlit as st
import pandas as pd
from datetime import date, datetime

import db
import scoring as sc
from config import (
    SECTIONS, QUESTION_MAP, ANS,
    WYMIAR_ETATU_OPTIONS, STATUS_OPTIONS, ABACUS,
)
from pdf_generator import generate_individual_pdf, generate_aggregate_pdf
from excel_generator import generate_aggregate_excel, generate_individual_excel

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Audyt Akt Osobowych | Abacus",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CSS – styl Abacus
# ─────────────────────────────────────────────
st.markdown(
    """
<style>
/* Sidebar */
[data-testid="stSidebar"] {
    background: #f4f6f8 !important;
}
/* Nagłówek aplikacji */
.app-header {
    background: linear-gradient(135deg, #0d1b2a 0%, #1b2d45 100%);
    padding: 1.2rem 1.6rem;
    border-radius: 10px;
    margin-bottom: 1.2rem;
    color: white;
}
.app-header h1 {
    margin: 0; font-size: 1.5rem; font-weight: 700; color: white;
}
.app-header p {
    margin: 0.2rem 0 0 0; font-size: 0.82rem; color: #cfd8e3;
}
/* Sekcja formularza */
.section-header {
    background: #f0f4f8;
    border-left: 4px solid #1b2d45;
    padding: 0.5rem 0.8rem;
    border-radius: 0 6px 6px 0;
    margin: 0.8rem 0 0.4rem 0;
    font-weight: 600;
    color: #0d1b2a;
}
/* Badge ryzyka */
.risk-low  { background:#eafaf1; color:#27ae60; padding:4px 12px; border-radius:20px; font-weight:700; }
.risk-mid  { background:#fef9e7; color:#e67e22; padding:4px 12px; border-radius:20px; font-weight:700; }
.risk-high { background:#fde8e8; color:#c0392b; padding:4px 12px; border-radius:20px; font-weight:700; }
/* Karta pracownika */
.worker-card {
    background: white; border: 1px solid #dee2e6; border-radius: 8px;
    padding: 1rem 1.2rem; margin-bottom: 0.5rem;
}
/* LP adnotacja */
.lp-note { color:#6c757d; font-size:0.8rem; font-style:italic; }
/* Warunkowe adnotacja */
.cond-note { color:#856404; font-size:0.8rem; font-style:italic; }
/* Submit btn */
div[data-testid="stFormSubmitButton"] > button {
    background: #1b2d45; color: white; font-weight: 700;
    padding: 0.6rem 2rem; border-radius: 6px; border: none;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def risk_badge(level: str) -> str:
    cls = {"niskie": "risk-low", "średnie": "risk-mid", "wysokie": "risk-high"}.get(level, "risk-low")
    emoji = sc.RISK_EMOJI.get(level, "")
    return f'<span class="{cls}">{emoji} {level.upper()}</span>'


def format_date(d) -> str:
    if isinstance(d, date):
        return d.strftime("%d.%m.%Y")
    return str(d) if d else "—"


def init_form_state():
    """Inicjalizuje session_state dla formularza nowego audytu."""
    defaults = {
        "f_firma": "",
        "f_imie": "",
        "f_nazwisko": "",
        "f_stanowisko": "",
        "f_data_zatrudnienia": date.today(),
        "f_pesel": "",
        "f_status": "aktualny",
        "f_wymiar": "Pełny etat",
        "f_min_wynagrodzenie": "TAK",
        "f_data_weryfikacji": date.today(),
        "f_weryfikujacy": "",
        "f_weryfikujacy_stanowisko": "",
        "form_step": "new",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Inicjalizuj odpowiedzi dla pytań
    for q_id, q in QUESTION_MAP.items():
        key = f"f_{q_id}"
        if key not in st.session_state:
            st.session_state[key] = ANS.get(q.get("ans", "tak_nie"), ["TAK", "NIE"])[0]
        comment_key = f"f_{q_id}_comment"
        if comment_key not in st.session_state:
            st.session_state[comment_key] = ""


def reset_form():
    keys_to_del = [k for k in st.session_state if k.startswith("f_")]
    for k in keys_to_del:
        del st.session_state[k]
    if "form_step" in st.session_state:
        del st.session_state["form_step"]
    init_form_state()


def get_current_answers() -> dict:
    """Zbiera aktualne odpowiedzi z session_state."""
    answers = {}
    for q_id in QUESTION_MAP:
        answers[q_id] = st.session_state.get(f"f_{q_id}")
    return answers


def should_show_question(q: dict, status: str, wymiar: str, answers: dict) -> bool:
    """Sprawdza czy pytanie powinno być widoczne."""
    q_applies = q.get("applies_to_status", None)
    if q_applies is not None and status not in q_applies:
        return False

    condition = q.get("condition")
    if condition:
        if condition == "B10_fp" and wymiar == "Pełny etat":
            return False
        elif condition == "D1_not_nd" and answers.get("D1") == "ND":
            return False
        elif condition == "E1_not_nd" and answers.get("E1") == "ND":
            return False
        elif condition == "P11_zcna" and answers.get("B16") != "TAK":
            return False
    return True


def render_question(q: dict, status: str, wymiar: str, answers: dict):
    """Renderuje pojedyncze pytanie formularza."""
    q_id = q["id"]
    key = f"f_{q_id}"
    q_status = q.get("status", "obowiązkowe")
    ans_type = q.get("ans", "tak_nie")
    options = ANS.get(ans_type, ["TAK", "NIE"])

    # Tytuł pytania z badge'em statusu
    status_badge = {"obowiązkowe": "🔴", "warunkowe": "🟡", "dobrowolne": "🟢"}.get(q_status, "")
    label = f"{status_badge} **{q['text']}**"

    col1, col2 = st.columns([3, 1])
    with col1:
        if q.get("lp_note"):
            st.markdown(
                '<span class="lp-note">ℹ️ Wymaga weryfikacji z listą płac</span>',
                unsafe_allow_html=True,
            )
        if q_status == "warunkowe":
            st.markdown(
                '<span class="cond-note">📌 Pytanie warunkowe – uzupełnij, jeśli dotyczy pracownika</span>',
                unsafe_allow_html=True,
            )

    # Poziomy radio dla krótkich list, pionowy dla dłuższych
    horizontal = len(options) <= 3

    current = st.session_state.get(key, options[0])
    idx = options.index(current) if current in options else 0

    answer = st.radio(
        label,
        options,
        index=idx,
        key=key,
        horizontal=horizontal,
    )

    # Uwaga do pytania A4
    if q.get("uwaga"):
        st.info(f"📋 {q['uwaga']}")

    # Dodatkowy komentarz dla P1 gdy TAK
    if q.get("extra_comment") and answer == "TAK":
        st.text_input(
            "Komentarz: Czy ewidencja pokrywa się z wnioskami urlopowymi i stanem faktycznym?",
            key=f"f_{q_id}_comment",
            placeholder="Opcjonalny komentarz...",
        )


def render_section(section: dict, status: str, wymiar: str, answers: dict):
    """Renderuje całą sekcję formularza."""
    with st.expander(f"**{section['title']}**", expanded=True):
        st.caption(section["desc"])

        visible_count = 0
        for q in section["questions"]:
            if should_show_question(q, status, wymiar, answers):
                render_question(q, status, wymiar, answers)
                st.markdown("---")
                visible_count += 1

        if visible_count == 0:
            st.info("Brak pytań mających zastosowanie w tej sekcji.")


def validate_basic_fields() -> list[str]:
    """Waliduje pola podstawowe. Zwraca listę błędów."""
    errors = []
    if not st.session_state.get("f_firma", "").strip():
        errors.append("Nazwa firmy jest wymagana.")
    if not st.session_state.get("f_imie", "").strip():
        errors.append("Imię pracownika jest wymagane.")
    if not st.session_state.get("f_nazwisko", "").strip():
        errors.append("Nazwisko pracownika jest wymagane.")
    if not st.session_state.get("f_stanowisko", "").strip():
        errors.append("Stanowisko jest wymagane.")
    if not st.session_state.get("f_pesel", "").strip():
        errors.append("PESEL jest wymagany.")
    if not st.session_state.get("f_weryfikujacy", "").strip():
        errors.append("Imię i nazwisko osoby weryfikującej jest wymagane.")
    return errors


# ─────────────────────────────────────────────
#  STRONY APLIKACJI
# ─────────────────────────────────────────────

def page_nowy_audyt():
    st.markdown(
        """<div class="app-header">
        <h1>🗂️ Nowy Audyt Akt Osobowych</h1>
        <p>Wypełnij formularz audytowy. Sekcje wyświetlane są zgodnie ze statusem pracownika.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    init_form_state()

    # ── Krok 1: Dane podstawowe ──────────────────
    st.subheader("1️⃣ Dane podstawowe")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("🏢 Nazwa firmy klienta *", key="f_firma", placeholder="np. XYZ sp. z o.o.")
        st.text_input("Imię pracownika *", key="f_imie")
        st.text_input("Stanowisko *", key="f_stanowisko")
        st.text_input("PESEL *", key="f_pesel", max_chars=11)
    with col2:
        st.text_input("Nazwisko pracownika *", key="f_nazwisko")
        st.date_input("Data rozpoczęcia zatrudnienia *", key="f_data_zatrudnienia")

        status = st.selectbox(
            "Status pracownika *",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(st.session_state.get("f_status", "aktualny")),
            format_func=lambda x: "✅ Aktualnie zatrudniony" if x == "aktualny" else "📤 Były pracownik",
            key="f_status",
        )

    st.divider()

    # Pobieramy aktualny status i wymiar do logiki
    current_status = st.session_state.get("f_status", "aktualny")
    current_wymiar = st.session_state.get("f_wymiar", "Pełny etat")

    # ── Krok 2: Warunki pracy (tylko aktualny) ───
    if current_status == "aktualny":
        st.subheader("2️⃣ Warunki zatrudnienia")
        col1, col2 = st.columns(2)
        with col1:
            wymiar_options = WYMIAR_ETATU_OPTIONS
            curr_idx = wymiar_options.index(current_wymiar) if current_wymiar in wymiar_options else 0
            st.selectbox(
                "Wymiar czasu pracy",
                wymiar_options,
                index=curr_idx,
                key="f_wymiar",
            )
            current_wymiar = st.session_state.get("f_wymiar", "Pełny etat")

            # Pole tekstowe jeśli "Inny"
            if current_wymiar == "Inny":
                st.text_input("Podaj wymiar etatu:", key="f_wymiar_opis", placeholder="np. 1/3 etatu")

        with col2:
            st.radio(
                "Czy pracownik osiąga minimalne wynagrodzenie na dzień sprawdzania?",
                ["TAK", "NIE"],
                key="f_min_wynagrodzenie",
                horizontal=True,
            )
        st.divider()

    # Zbieramy odpowiedzi do logiki warunkowej
    answers = get_current_answers()

    # ── Sekcje formularza ────────────────────────
    st.subheader("3️⃣ Weryfikacja dokumentacji")

    for section in SECTIONS:
        if current_status not in section.get("applies_to", []):
            continue
        render_section(section, current_status, current_wymiar, answers)

    st.divider()

    # ── Krok: Dane weryfikatora ──────────────────
    st.subheader("4️⃣ Dane osoby weryfikującej")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.date_input("Data weryfikacji *", key="f_data_weryfikacji")
    with col2:
        st.text_input("Imię i nazwisko weryfikującego *", key="f_weryfikujacy")
    with col3:
        st.text_input("Stanowisko weryfikującego *", key="f_weryfikujacy_stanowisko")

    st.divider()

    # ── Przycisk Zapisz ──────────────────────────
    col_save, col_reset, _ = st.columns([2, 2, 6])
    with col_save:
        save_clicked = st.button("💾 Zapisz audyt", type="primary", use_container_width=True)
    with col_reset:
        if st.button("🔄 Resetuj formularz", use_container_width=True):
            reset_form()
            st.rerun()

    if save_clicked:
        errors = validate_basic_fields()
        if errors:
            for e in errors:
                st.error(f"❌ {e}")
        else:
            # Oblicz wyniki
            final_answers = get_current_answers()
            final_status = st.session_state.get("f_status", "aktualny")
            final_wymiar = st.session_state.get("f_wymiar", "Pełny etat")

            scores = sc.calculate_scores(final_answers, final_status, final_wymiar)

            # Buduj rekord
            audyt_data = {
                "firma": st.session_state.get("f_firma", "").strip(),
                "imie": st.session_state.get("f_imie", "").strip(),
                "nazwisko": st.session_state.get("f_nazwisko", "").strip(),
                "stanowisko": st.session_state.get("f_stanowisko", "").strip(),
                "data_zatrudnienia": format_date(st.session_state.get("f_data_zatrudnienia")),
                "pesel": st.session_state.get("f_pesel", "").strip(),
                "status_pracownika": final_status,
                "wymiar_etatu": final_wymiar if final_status == "aktualny" else None,
                "minimalne_wynagrodzenie": st.session_state.get("f_min_wynagrodzenie") if final_status == "aktualny" else None,
                "odpowiedzi": final_answers,
                "braki_obowiazkowe": scores["obligatory_gaps"],
                "braki_warunkowe": scores["conditional_gaps"],
                "braki_dobrowolne": scores["voluntary_gaps"],
                "kompletnosc_procent": scores["completeness"],
                "poziom_ryzyka": scores["risk_level"],
                "gap_list": scores["gap_list"],
                "data_weryfikacji": format_date(st.session_state.get("f_data_weryfikacji")),
                "weryfikujacy_imie_nazwisko": st.session_state.get("f_weryfikujacy", "").strip(),
                "weryfikujacy_stanowisko": st.session_state.get("f_weryfikujacy_stanowisko", "").strip(),
            }

            new_id = db.save_audyt(audyt_data)
            st.session_state["last_saved_id"] = new_id
            st.success(f"✅ Audyt zapisany! ID: {new_id}")
            st.balloons()

            # Reset i przejdź do szczegółów
            reset_form()
            st.session_state["view_audyt_id"] = new_id
            st.session_state["page"] = "szczegoly"
            st.rerun()


def page_lista_audytow():
    st.markdown(
        """<div class="app-header">
        <h1>📋 Lista Audytów</h1>
        <p>Przeglądaj i zarządzaj zapisanymi audytami pracowników.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    audyty = db.get_all_audyty()

    if not audyty:
        st.info("Brak zapisanych audytów. Zacznij od dodania nowego audytu.")
        return

    # Filtry
    col1, col2, col3 = st.columns(3)
    firmy = sorted(set(a["firma"] for a in audyty))
    with col1:
        f_firma = st.selectbox("Filtruj wg firmy", ["Wszystkie"] + firmy)
    with col2:
        f_status = st.selectbox("Status pracownika", ["Wszyscy", "aktualny", "były"])
    with col3:
        f_risk = st.selectbox("Poziom ryzyka", ["Wszystkie", "niskie", "średnie", "wysokie"])

    filtered = audyty
    if f_firma != "Wszystkie":
        filtered = [a for a in filtered if a["firma"] == f_firma]
    if f_status != "Wszyscy":
        filtered = [a for a in filtered if a["status_pracownika"] == f_status]
    if f_risk != "Wszystkie":
        filtered = [a for a in filtered if a["poziom_ryzyka"] == f_risk]

    st.caption(f"Wyświetlono: {len(filtered)} / {len(audyty)} audytów")
    st.divider()

    if not filtered:
        st.warning("Brak audytów spełniających wybrane kryteria.")
        return

    for a in filtered:
        risk = a.get("poziom_ryzyka", "niskie")
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1.5])
            with col1:
                st.markdown(f"**{a['imie']} {a['nazwisko']}**")
                st.caption(f"🏢 {a['firma']}")
            with col2:
                st.caption(f"💼 {a['stanowisko']}")
                st.caption(f"📅 {a['data_zatrudnienia']}")
            with col3:
                st.caption(f"🏷️ {a['status_pracownika'].capitalize()}")
                st.caption(f"📊 Kompletność: {a['kompletnosc_procent']:.1f}%")
            with col4:
                st.markdown(risk_badge(risk), unsafe_allow_html=True)
                st.caption(
                    f"OBL:{a['braki_obowiazkowe']} WAR:{a['braki_warunkowe']} DOB:{a['braki_dobrowolne']}"
                )
            with col5:
                if st.button("🔍 Szczegóły", key=f"detail_{a['id']}"):
                    st.session_state["view_audyt_id"] = a["id"]
                    st.session_state["page"] = "szczegoly"
                    st.rerun()
                if st.button("🗑️", key=f"del_{a['id']}", help="Usuń audyt"):
                    db.delete_audyt(a["id"])
                    st.rerun()
            st.divider()


def page_szczegoly():
    audyt_id = st.session_state.get("view_audyt_id")
    if not audyt_id:
        st.warning("Nie wybrano audytu.")
        return

    a = db.get_audyt_by_id(audyt_id)
    if not a:
        st.error("Audyt nie istnieje.")
        return

    # Przycisk wstecz
    if st.button("← Wróć do listy"):
        st.session_state["page"] = "lista"
        st.rerun()

    st.markdown(
        f"""<div class="app-header">
        <h1>🗂️ {a['imie']} {a['nazwisko']}</h1>
        <p>{a['firma']} | {a['stanowisko']} | {a['status_pracownika'].capitalize()}</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # Dane i wynik
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Kompletność", f"{a['kompletnosc_procent']:.1f}%")
    col2.metric("Braki obowiązkowe", a["braki_obowiazkowe"])
    col3.metric("Braki warunkowe", a["braki_warunkowe"])
    col4.metric("Braki dobrowolne", a["braki_dobrowolne"])

    risk = a.get("poziom_ryzyka", "niskie")
    st.markdown(
        f"**Poziom ryzyka:** {risk_badge(risk)}",
        unsafe_allow_html=True,
    )
    st.caption(f"Data weryfikacji: {a.get('data_weryfikacji','—')} | Weryfikujący: {a.get('weryfikujacy_imie_nazwisko','—')} ({a.get('weryfikujacy_stanowisko','—')})")

    st.divider()

    # Lista braków
    gap_list = a.get("gap_list", [])
    if gap_list:
        st.subheader(f"⚠️ Lista braków dokumentacyjnych ({len(gap_list)} poz.)")

        STATUS_COLORS = {
            "obowiązkowe": "🔴",
            "warunkowe": "🟡",
            "dobrowolne": "🟢",
        }

        obowiązkowe = [g for g in gap_list if g["status"] == "obowiązkowe"]
        warunkowe = [g for g in gap_list if g["status"] == "warunkowe"]
        dobrowolne = [g for g in gap_list if g["status"] == "dobrowolne"]

        def render_gap_group(title, gaps, color):
            if not gaps:
                return
            st.markdown(f"**{color} {title} ({len(gaps)} poz.)**")
            for g in gaps:
                with st.container():
                    c1, c2 = st.columns([4, 2])
                    with c1:
                        st.markdown(f"**[{g['id']}]** {g['text']}")
                        st.caption(f"Sekcja: {g['section']} | Udzielona odpowiedź: {g['answer']}")
                    with c2:
                        st.warning(f"⚡ {g['recommendation']}")
                st.markdown("---")

        render_gap_group("Braki obowiązkowe – NATYCHMIASTOWE DZIAŁANIE", obowiązkowe, "🔴")
        render_gap_group("Braki warunkowe", warunkowe, "🟡")
        render_gap_group("Braki dobrowolne – uzupełnić w 14 dni", dobrowolne, "🟢")

    else:
        st.success("✅ Brak stwierdzonych braków dokumentacyjnych!")

    st.divider()

    # Konsekwencje prawne
    with st.expander("⚖️ Konsekwencje prawne – informacja"):
        from config import LEGAL_CONSEQUENCES
        st.markdown(LEGAL_CONSEQUENCES)

    st.divider()

    # Pobierz PDF / Excel
    st.subheader("📥 Eksport raportu")
    scores = {
        "obligatory_total": a["braki_obowiazkowe"],
        "obligatory_gaps": a["braki_obowiazkowe"],
        "conditional_total": a["braki_warunkowe"],
        "conditional_gaps": a["braki_warunkowe"],
        "voluntary_total": a["braki_dobrowolne"],
        "voluntary_gaps": a["braki_dobrowolne"],
        "risk_pct": a.get("kompletnosc_procent", 100),
        "risk_level": a.get("poziom_ryzyka", "niskie"),
        "completeness": a.get("kompletnosc_procent", 100),
        "gap_list": gap_list,
    }

    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_bytes = generate_individual_pdf(a, scores)
            fname = f"audyt_{a['nazwisko']}_{a['imie']}_{date.today().strftime('%Y%m%d')}.pdf"
            st.download_button(
                "📄 Pobierz raport PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Błąd generowania PDF: {e}")

    with col2:
        try:
            excel_bytes = generate_individual_excel(a, gap_list)
            fname_xl = f"braki_{a['nazwisko']}_{a['imie']}_{date.today().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                "📊 Pobierz listę braków (Excel)",
                data=excel_bytes,
                file_name=fname_xl,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Błąd generowania Excel: {e}")


def page_raport_zbiorczy():
    st.markdown(
        """<div class="app-header">
        <h1>📊 Raport Zbiorczy</h1>
        <p>Przegląd wyników audytów dla wszystkich firm i pracowników.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    audyty = db.get_all_audyty()

    if not audyty:
        st.info("Brak danych. Dodaj pierwsze audyty, aby zobaczyć raport zbiorczy.")
        return

    # Filtry
    st.subheader("🔍 Filtry")
    firmy = sorted(set(a["firma"] for a in audyty))
    col1, col2, col3 = st.columns(3)
    with col1:
        f_firma = st.selectbox("Firma", ["Wszystkie"] + firmy, key="rb_firma")
    with col2:
        f_status = st.selectbox("Status pracownika", ["Wszyscy", "aktualny", "były"], key="rb_status")
    with col3:
        f_risk = st.selectbox("Poziom ryzyka", ["Wszystkie", "niskie", "średnie", "wysokie"], key="rb_risk")

    filtered = audyty
    if f_firma != "Wszystkie":
        filtered = [a for a in filtered if a["firma"] == f_firma]
    if f_status != "Wszyscy":
        filtered = [a for a in filtered if a["status_pracownika"] == f_status]
    if f_risk != "Wszystkie":
        filtered = [a for a in filtered if a["poziom_ryzyka"] == f_risk]

    st.divider()

    if not filtered:
        st.warning("Brak audytów spełniających wybrane kryteria.")
        return

    # Statystyki
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pracownicy", len(filtered))
    col2.metric(
        "Wysokie ryzyko",
        sum(1 for a in filtered if a["poziom_ryzyka"] == "wysokie"),
    )
    col3.metric(
        "Śr. kompletność",
        f"{sum(a['kompletnosc_procent'] for a in filtered) / len(filtered):.1f}%",
    )
    col4.metric(
        "Łączne braki OBL",
        sum(a["braki_obowiazkowe"] for a in filtered),
    )

    st.divider()

    # Tabela
    RISK_EM = {"niskie": "🟢", "średnie": "🟡", "wysokie": "🔴"}
    df_rows = []
    for a in filtered:
        df_rows.append({
            "Firma": a["firma"],
            "Pracownik": f"{a['imie']} {a['nazwisko']}",
            "Stanowisko": a["stanowisko"],
            "Status": a["status_pracownika"],
            "Braki OBL": a["braki_obowiazkowe"],
            "Braki WAR": a["braki_warunkowe"],
            "Braki DOB": a["braki_dobrowolne"],
            "Kompletność": f"{a['kompletnosc_procent']:.1f}%",
            "Ryzyko": f"{RISK_EM.get(a['poziom_ryzyka'],'?')} {a['poziom_ryzyka'].upper()}",
        })

    df = pd.DataFrame(df_rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Braki OBL": st.column_config.NumberColumn(format="%d"),
            "Braki WAR": st.column_config.NumberColumn(format="%d"),
            "Braki DOB": st.column_config.NumberColumn(format="%d"),
        },
    )

    st.divider()

    # Eksporty zbiorcze
    st.subheader("📥 Eksport raportu zbiorczego")
    col1, col2 = st.columns(2)

    with col1:
        try:
            excel_bytes = generate_aggregate_excel(filtered)
            fname_xl = f"raport_zbiorczy_{date.today().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                "📊 Pobierz raport zbiorczy (Excel)",
                data=excel_bytes,
                file_name=fname_xl,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Błąd generowania Excel: {e}")

    with col2:
        try:
            pdf_bytes = generate_aggregate_pdf(filtered)
            fname_pdf = f"raport_zbiorczy_{date.today().strftime('%Y%m%d')}.pdf"
            st.download_button(
                "📄 Pobierz raport zbiorczy (PDF)",
                data=pdf_bytes,
                file_name=fname_pdf,
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Błąd generowania PDF: {e}")


# ─────────────────────────────────────────────
#  STRONA: UPLOAD AI
# ─────────────────────────────────────────────

def _get_api_key() -> str | None:
    """Pobiera klucz API z st.secrets lub zmiennej środowiskowej.
    (Niewykorzystywany w trybie lokalnym – pozostawiony dla zgodności.)"""
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        import os
        return os.environ.get("ANTHROPIC_API_KEY")


def _build_doc_dropdown_options() -> dict[str, str]:
    """Buduje słownik {label: doc_id} do dropdownu ręcznego przypisania."""
    options = {"— wybierz dokument —": None}
    section_names = {"A": "Część A – Rekrutacja", "B": "Część B – Zatrudnienie",
                     "C": "Część C – Ustanie", "D": "Część D – Kary",
                     "E": "Część E – Trzeźwość", "P": "Pozaaktowa"}
    current_section = None
    for section in SECTIONS:
        sid = section["id"]
        for q in section["questions"]:
            q_id = q["id"]
            if sid != current_section:
                current_section = sid
                options[f"── {section_names.get(sid, sid)} ──"] = None
            options[f"  {q_id} – {q['text']}"] = q_id
    return options


def page_upload_ai():
    from ai_analyzer import (
        analyze_uploaded_files, results_to_answers,
        FILENAME_PATTERNS, needs_payroll_review,
    )

    st.markdown(
        """<div class="app-header">
        <h1>🔍 Analiza lokalna – Upload Dokumentów</h1>
        <p>Wgraj skany PDF pracownika → analiza lokalna (bez API) identyfikuje dokumenty → gotowy raport audytowy.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # Tryb lokalny – klucz API niepotrzebny (dane nie opuszczają serwera).
    api_key = None

    # ── Stan analizy ─────────────────────────────
    stage = st.session_state.get("ai_stage", "input")  # input → analyzing → review → summary

    # ── ETAP: DANE PODSTAWOWE + UPLOAD ───────────
    if stage == "input":
        st.subheader("1️⃣ Dane pracownika")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("🏢 Firma klienta *", key="ai_firma")
            st.text_input("Imię *", key="ai_imie")
            st.text_input("Stanowisko *", key="ai_stanowisko")
            st.text_input("PESEL *", key="ai_pesel", max_chars=11)
        with col2:
            st.text_input("Nazwisko *", key="ai_nazwisko")
            st.date_input("Data zatrudnienia *", key="ai_data_zatrudnienia")
            st.selectbox(
                "Status *",
                STATUS_OPTIONS,
                format_func=lambda x: "✅ Aktualnie zatrudniony" if x == "aktualny" else "📤 Były pracownik",
                key="ai_status",
            )

        if st.session_state.get("ai_status") == "aktualny":
            col1, col2 = st.columns(2)
            with col1:
                st.selectbox("Wymiar etatu", WYMIAR_ETATU_OPTIONS, key="ai_wymiar")
            with col2:
                st.radio("Osiąga min. wynagrodzenie?", ["TAK", "NIE"],
                         key="ai_min_wynagrodzenie", horizontal=True)

        st.divider()
        st.subheader("2️⃣ Wgraj dokumenty PDF")

        st.info(
            "💡 **Wskazówka:** Nazwy plików przyspieszają identyfikację. "
            "Przykłady: `B3_umowa_o_prace.pdf`, `A6_orzeczenie.pdf`, `bhp.pdf`\n\n"
            "Możesz wgrać pojedyncze pliki lub wielostronicowe PDF-y (każda strona = osobny dokument)."
        )

        uploaded = st.file_uploader(
            "Wybierz pliki PDF (możesz zaznaczyć wiele naraz)",
            type=["pdf"],
            accept_multiple_files=True,
            key="ai_uploaded_files",
        )

        if uploaded:
            st.success(f"✅ Wgrano {len(uploaded)} plik(ów)")
            for f in uploaded:
                st.caption(f"📄 {f.name}")

        st.divider()
        st.subheader("3️⃣ Dane weryfikatora")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.date_input("Data weryfikacji", key="ai_data_weryfikacji")
        with col2:
            st.text_input("Weryfikujący – imię i nazwisko", key="ai_weryfikujacy")
        with col3:
            st.text_input("Stanowisko weryfikującego", key="ai_weryfikujacy_stanowisko")

        st.divider()

        col_start, col_reset, _ = st.columns([2, 2, 6])
        with col_start:
            start = st.button(
                "🔍 Analizuj dokumenty",
                type="primary",
                use_container_width=True,
                disabled=not uploaded,
            )
        with col_reset:
            if st.button("🔄 Resetuj", use_container_width=True):
                for k in [k for k in st.session_state if k.startswith("ai_")]:
                    del st.session_state[k]
                st.rerun()

        if start:
            if not st.session_state.get("ai_firma", "").strip():
                st.error("❌ Podaj nazwę firmy.")
                return
            if not uploaded:
                st.error("❌ Wgraj przynajmniej jeden plik PDF.")
                return
            st.session_state["ai_stage"] = "analyzing"
            st.rerun()

    # ── ETAP: ANALIZA ────────────────────────────
    elif stage == "analyzing":
        st.subheader("🔄 Trwa analiza dokumentów...")

        uploaded = st.session_state.get("ai_uploaded_files", [])
        if not uploaded:
            st.error("Brak plików do analizy. Wróć do poprzedniego kroku.")
            st.session_state["ai_stage"] = "input"
            st.rerun()
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        results_holder = []

        def progress_cb(current, total, filename):
            pct = int(current / total * 100) if total > 0 else 100
            progress_bar.progress(pct)
            if current < total:
                status_text.markdown(f"📄 Analizuję: **{filename}** ({current + 1}/{total})")
            else:
                status_text.markdown("✅ Analiza zakończona!")

        try:
            results = analyze_uploaded_files(uploaded, api_key, progress_cb)
            st.session_state["ai_results"] = results

            # Podziel na pewne i wątpliwe
            pewne = [r for r in results if r["status"] == "PEWNY" and r["document_id"]]
            watpliwe = [r for r in results if r["status"] == "WĄTPLIWY"]

            st.session_state["ai_confirmed"] = pewne.copy()
            st.session_state["ai_queue"] = watpliwe.copy()
            st.session_state["ai_queue_idx"] = 0

            if watpliwe:
                st.session_state["ai_stage"] = "review"
            else:
                st.session_state["ai_stage"] = "summary"
            st.rerun()

        except Exception as e:
            st.error(f"❌ Błąd podczas analizy: {e}")
            if st.button("← Wróć"):
                st.session_state["ai_stage"] = "input"
                st.rerun()

    # ── ETAP: KOLEJKA WĄTPLIWYCH ─────────────────
    elif stage == "review":
        queue = st.session_state.get("ai_queue", [])
        idx = st.session_state.get("ai_queue_idx", 0)
        confirmed = st.session_state.get("ai_confirmed", [])

        if idx >= len(queue):
            st.session_state["ai_stage"] = "summary"
            st.rerun()
            return

        item = queue[idx]
        total_q = len(queue)

        st.subheader(f"🔍 Weryfikacja wątpliwych dokumentów ({idx + 1}/{total_q})")
        st.progress((idx) / total_q)

        st.markdown("---")
        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown(f"**📄 Plik:** `{item['filename']}`")
            st.markdown(f"**🔍 Wynik analizy:** {item['reason']}")
            if item.get("document_id"):
                q_text = QUESTION_MAP.get(item["document_id"], {}).get("text", "?")
                st.info(f"Propozycja: **{item['document_id']}** – {q_text}")
            else:
                st.warning("Nie rozpoznano dokumentu")

            if item.get("image_png"):
                st.image(item["image_png"], caption="Nagłówek dokumentu (top 25%)", use_container_width=True)

        with col2:
            st.markdown("**Co chcesz zrobić z tym plikiem?**")

            # Opcja 1: Akceptuj propozycję
            if item.get("document_id"):
                q_text = QUESTION_MAP.get(item["document_id"], {}).get("text", "")
                if st.button(
                    f"✅ Akceptuj: {item['document_id']} – {q_text}",
                    use_container_width=True,
                    key="btn_accept",
                ):
                    confirmed.append({**item, "status": "PEWNY"})
                    st.session_state["ai_confirmed"] = confirmed
                    st.session_state["ai_queue_idx"] = idx + 1
                    st.rerun()

            # Opcja 2: Przypisz ręcznie
            st.markdown("**📋 Lub przypisz ręcznie:**")
            doc_options = _build_doc_dropdown_options()
            labels = list(doc_options.keys())

            selected_label = st.selectbox(
                "Wybierz dokument z listy",
                labels,
                key=f"manual_select_{idx}",
            )
            selected_id = doc_options.get(selected_label)

            if st.button("📌 Przypisz wybrany", use_container_width=True, key="btn_assign",
                         disabled=not selected_id):
                q_text = QUESTION_MAP.get(selected_id, {}).get("text", "")
                confirmed.append({
                    **item,
                    "document_id": selected_id,
                    "status": "PEWNY",
                    "source": "RĘCZNIE",
                    "reason": f"Ręcznie przypisany jako {selected_id} – {q_text}",
                })
                st.session_state["ai_confirmed"] = confirmed
                st.session_state["ai_queue_idx"] = idx + 1
                st.rerun()

            st.divider()

            # Opcja 3: Pomiń
            if st.button("⏭️ Pomiń (oznacz jako BRAK)", use_container_width=True, key="btn_skip"):
                st.session_state["ai_queue_idx"] = idx + 1
                st.rerun()

    # ── ETAP: PODSUMOWANIE I ZAPIS ───────────────
    elif stage == "summary":
        confirmed = st.session_state.get("ai_confirmed", [])
        all_results = st.session_state.get("ai_results", [])

        st.subheader("📊 Podsumowanie analizy")

        col1, col2, col3 = st.columns(3)
        col1.metric("Wszystkich plików/stron", len(all_results))
        col2.metric("Zidentyfikowanych pewnie", len([r for r in all_results if r["status"] == "PEWNY"]))
        col3.metric("Potwierdzonych przez użytkownika", len(confirmed))

        st.divider()

        if confirmed:
            st.markdown("**✅ Zidentyfikowane dokumenty:**")
            for r in confirmed:
                q_text = QUESTION_MAP.get(r["document_id"], {}).get("text", "?")
                src = "🔍 Auto" if r.get("source") == "LOKALNIE" else "👤 Ręcznie"
                st.markdown(f"- `{r['document_id']}` – {q_text} &nbsp; {src}")
        else:
            st.warning("Brak zidentyfikowanych dokumentów.")

        # Pozycje wymagające weryfikacji z listą płac (placeholdery z auto-detekcji)
        pr = needs_payroll_review(confirmed)
        if pr:
            st.warning(
                "⚠️ Wartości wstawione automatycznie, wymagają weryfikacji z listą płac: "
                + ", ".join(pr)
            )

        unidentified = [r for r in all_results if r not in confirmed and r["status"] == "WĄTPLIWY"]
        if unidentified:
            with st.expander(f"⚠️ Nieprzypisane pliki ({len(unidentified)})"):
                for r in unidentified:
                    st.caption(f"❓ {r['filename']} – {r['reason']}")

        st.divider()
        st.subheader("💾 Zapisz audyt")

        # Konwertuj potwierdzone wyniki na odpowiedzi formularza
        answers = results_to_answers(confirmed)

        status = st.session_state.get("ai_status", "aktualny")
        wymiar = st.session_state.get("ai_wymiar", "Pełny etat")
        scores = sc.calculate_scores(answers, status, wymiar)

        # Pokaż ryzyko
        risk = scores["risk_level"]
        st.markdown(f"**Wyliczony poziom ryzyka:** {risk_badge(risk)}", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Braki obowiązkowe", scores["obligatory_gaps"])
        col2.metric("Braki warunkowe", scores["conditional_gaps"])
        col3.metric("Kompletność", f"{scores['completeness']:.1f}%")

        st.divider()

        col_save, col_back, _ = st.columns([2, 2, 6])
        with col_save:
            if st.button("💾 Zapisz audyt", type="primary", use_container_width=True):
                audyt_data = {
                    "firma": st.session_state.get("ai_firma", "").strip(),
                    "imie": st.session_state.get("ai_imie", "").strip(),
                    "nazwisko": st.session_state.get("ai_nazwisko", "").strip(),
                    "stanowisko": st.session_state.get("ai_stanowisko", "").strip(),
                    "data_zatrudnienia": format_date(st.session_state.get("ai_data_zatrudnienia")),
                    "pesel": st.session_state.get("ai_pesel", "").strip(),
                    "status_pracownika": status,
                    "wymiar_etatu": wymiar if status == "aktualny" else None,
                    "minimalne_wynagrodzenie": st.session_state.get("ai_min_wynagrodzenie") if status == "aktualny" else None,
                    "odpowiedzi": answers,
                    "braki_obowiazkowe": scores["obligatory_gaps"],
                    "braki_warunkowe": scores["conditional_gaps"],
                    "braki_dobrowolne": scores["voluntary_gaps"],
                    "kompletnosc_procent": scores["completeness"],
                    "poziom_ryzyka": scores["risk_level"],
                    "gap_list": scores["gap_list"],
                    "data_weryfikacji": format_date(st.session_state.get("ai_data_weryfikacji")),
                    "weryfikujacy_imie_nazwisko": st.session_state.get("ai_weryfikujacy", "").strip(),
                    "weryfikujacy_stanowisko": st.session_state.get("ai_weryfikujacy_stanowisko", "").strip(),
                }
                new_id = db.save_audyt(audyt_data)
                st.success(f"✅ Audyt zapisany! ID: {new_id}")
                st.balloons()

                # Wyczyść stan AI
                for k in [k for k in st.session_state if k.startswith("ai_")]:
                    del st.session_state[k]

                st.session_state["view_audyt_id"] = new_id
                st.session_state["page"] = "szczegoly"
                st.rerun()

        with col_back:
            if st.button("← Wróć do inputu", use_container_width=True):
                st.session_state["ai_stage"] = "input"
                st.rerun()


# ─────────────────────────────────────────────
#  SIDEBAR NAWIGACJA
# ─────────────────────────────────────────────

def sidebar_nav():
    with st.sidebar:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#0d1b2a,#1b2d45);
                        padding:1rem;border-radius:8px;margin-bottom:1rem;text-align:center">
                <div style="color:white;font-weight:700;font-size:1.1rem">🗂️ Audyt AO</div>
                <div style="color:#cfd8e3;font-size:0.75rem">{ABACUS['nazwa']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            all_audyty = db.get_all_audyty()
            n = len(all_audyty)
            high = sum(1 for a in all_audyty if a["poziom_ryzyka"] == "wysokie")
        except Exception:
            n, high = 0, 0

        st.metric("Zapisane audyty", n)
        if high > 0:
            st.metric("Wysokie ryzyko ⚠️", high)

        st.divider()

        menu_items = {
            "nowy": "✏️ Formularz ręczny",
            "upload_ai": "🔍 Analiza lokalna",
            "lista": "📋 Lista audytów",
            "szczegoly": "🔍 Szczegóły audytu",
            "raport": "📊 Raport zbiorczy",
        }

        if "page" not in st.session_state:
            st.session_state["page"] = "nowy"

        for key, label in menu_items.items():
            if key == "szczegoly" and not st.session_state.get("view_audyt_id"):
                continue
            active = st.session_state.get("page") == key
            if st.button(
                label,
                key=f"nav_{key}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state["page"] = key
                st.rerun()

        st.divider()
        st.caption(f"🌐 {ABACUS['www']}")
        st.caption(f"📧 {ABACUS['email']}")
        st.caption(f"📞 {ABACUS['tel']}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    sidebar_nav()

    page = st.session_state.get("page", "nowy")

    if page == "nowy":
        page_nowy_audyt()
    elif page == "upload_ai":
        page_upload_ai()
    elif page == "lista":
        page_lista_audytow()
    elif page == "szczegoly":
        page_szczegoly()
    elif page == "raport":
        page_raport_zbiorczy()
    else:
        page_nowy_audyt()


if __name__ == "__main__":
    main()
