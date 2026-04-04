# 🗂️ Audyt Akt Osobowych
### Abacus Centrum Księgowe sp. z o.o.

Aplikacja Streamlit do audytu teczek akt osobowych pracowników.
Narzędzie eksperckie dla biur rachunkowych i działów kadr.

---

## 📁 Struktura projektu

```
audyt-akt-osobowych/
├── app.py                  # Główna aplikacja Streamlit
├── config.py               # Konfiguracja sekcji i pytań formularza
├── db.py                   # Operacje na bazie SQLite
├── scoring.py              # Logika oceny braków i ryzyka
├── pdf_generator.py        # Generowanie PDF (ReportLab)
├── excel_generator.py      # Generowanie Excel (openpyxl)
├── seed_data.py            # Skrypt z przykładowymi danymi testowymi
├── requirements.txt        # Zależności Python
├── DejaVuSans.ttf          # Font (do pobrania – patrz niżej)
├── DejaVuSans-Bold.ttf     # Font Bold (do pobrania – patrz niżej)
├── audyty.db               # Baza SQLite (tworzona automatycznie)
└── README.md               # Ta dokumentacja
```

---

## ⚡ Uruchomienie lokalne

### 1. Wymagania
- Python 3.10 lub nowszy
- pip

### 2. Instalacja zależności

```bash
cd audyt-akt-osobowych
python -m pip install -r requirements.txt
```

### 3. (Zalecane) Pobierz font DejaVuSans dla poprawnych polskich znaków w PDF

Pobierz pliki z oficjalnego źródła:
- https://github.com/dejavu-fonts/dejavu-fonts/releases

Skopiuj do folderu aplikacji:
- `DejaVuSans.ttf`
- `DejaVuSans-Bold.ttf`

> Bez fontu PDF wygeneruje się na Helvetica – polskie znaki mogą nie wyświetlać się poprawnie.

### 4. Uruchomienie

```bash
python -m streamlit run app.py
```

Aplikacja otworzy się na `http://localhost:8501`

---

## 🧪 Dane testowe

Aby załadować przykładowe audyty demonstracyjne:

```bash
python seed_data.py
```

Załaduje 5 przykładowych pracowników z różnymi poziomami ryzyka.

---

## 🌐 Wdrożenie na Streamlit Cloud

1. Wgraj projekt do repozytorium GitHub (np. `mjstrus/audyt-akt-osobowych`)
2. Zaloguj się na https://share.streamlit.io
3. Kliknij „New app" → wskaż repozytorium i plik `app.py`
4. Dodaj fonty do repo lub skonfiguruj fallback

> **Uwaga:** Baza SQLite `audyty.db` jest przechowywana lokalnie na serwerze Streamlit Cloud.
> Przy restarcie instancji dane mogą zostać utracone. Dla trwałego przechowywania
> rozważ upgrade do Streamlit Community Cloud z persystencją lub podłączenie Supabase.

---

## 🔧 Możliwe rozszerzenia

- [ ] Logowanie użytkowników (streamlit-authenticator)
- [ ] Edycja istniejących audytów
- [ ] Powiadomienia e-mail przy wysokim ryzyku
- [ ] Integracja z Enova365 API
- [ ] Eksport do Google Drive
- [ ] Wersjonowanie szablonu pytań
- [ ] Rozszerzony audyt dla byłych pracowników (Dokumentacja Pozaaktowa)

---

## 📜 Logika formularza

### Pracownik aktualny
Sekcje: A, B, D, E, Dokumentacja Pozaaktowa (P1-P9, P11 warunkowo)

Logika warunkowa:
- Część B, pyt. 10 (FP): ukryte gdy pełny etat
- Część D, pyt. 2-3: ukryte gdy D1 = ND
- Część E, pyt. 2-3: ukryte gdy E1 = ND
- ZUS ZCNA (P11): widoczne tylko gdy B16 = TAK

### Pracownik były
Sekcje: tylko C + ZUS ZWUA (P10)

### Poziom ryzyka
- 0–15% braków obowiązkowych → 🟢 Niskie
- 16–40% → 🟡 Średnie
- >40% → 🔴 Wysokie

---

*Abacus Centrum Księgowe sp. z o.o. | ul. Zielona 13 lok 3, 24-100 Puławy*
*www.abacus24.pl | biuro@abacus24.pl | tel. 500 120 075*
