# Automaty Vibe na komputerze Krzysztofa (DESKTOP-SKOGFG5)

Stan na 2026-11-19. Trzy automaty = trzy demony Python + trzy taski w Harmonogramie zadań Windows. Kod źródłowy automatów: katalog `automaty/` w tym repo.

## Przegląd

| Task (Harmonogram) | Folder lokalny | Termin | Co robi |
|---|---|---|---|
| BiZU-Newsletter-Runner | bizu-server | co 14 dni (next_run_at w state.json; aktualnie 2026-12-01 09:00, wydanie #2) | cykl newslettera BiZU: propozycja tematów -> mail -> ręczne finalize |
| Rejestry-Urbanistyczne-Runner | rejestry-urbanistyczne | 1. dzień miesiąca 09:00 | pobiera 4 rejestry XLSX z wykazów Ursusa, raport za poprzedni miesiąc mailem |
| Inwestycje-Ursus-Runner | inwestycje-ursus | 1. dzień miesiąca 10:00 | podsumowanie inwestycji -> Google Doc na Drive |

Każdy task ma wyzwalacz przy logowaniu (+ kalendarzowy dla dwóch miesięcznych). Akcja: pythonw.exe <runner>.py, working dir = folder automatu.

## Wspólne zasady daemonów

- Pętla co 300 s; termin w state.json (next_run_at); lock .daemon.lock (24 h); log runner.log; przebiegi Vibe w runs/*.log
- Vibe headless: vibe -p <prompt> --auto-approve --trust --workdir <folder> --max-turns 120 --output text; sukces = "RESULT: OK" w ogonie logu
- Błąd: attempts+1, retry za 6 h, po 10 próbach next_run_at=9999 (czeka na run-now)
- Zaległy termin łapie się przy kolejnym logowaniu (now >= next_run_at)
- Ręcznie: python <runner>.py status | run-now | next <ISO>  (newsletter też: finalize [korekty])

## 1. Newsletter (automaty/newsletter_runner.py + proposal_prompt.txt + finalize_prompt.txt)

- Okno tematów: od dnia po poprzedniej wysyłce do dnia wykonania przebiegu (zmiana 2026-11-19; wcześniej 14 dni kończące się 2 dni przed wysyłką). Dla wydania 1.12: 18.11-1.12
- Faza proposal: Vibe zbiera tematy (FB przez r.jina.ai, zielonyursus.pl), mail z propozycją do krzysiekdc@gmail.com + plik proposal-<N>.md, phase=awaiting_approval
- Finalize (ręcznie): finalny newsletter mailem tylko do Krzyśka + archiwum w Drive (folder 13aZilfHN8X8A3AzbReLOR1JFSj6y4zrb), issue+1

## 2. Rejestry urbanistyczne (automaty/rejestry_runner.py + zadanie_rejestry_urbanistyczne.txt)

- Prompt: zadanie_rejestry_urbanistyczne.txt (lokalnie w .vibe, czytany na żywo)
- Auto-download: https://ursus.um.warszawa.pl/-/wykazy-za-rok-2026 (User-Agent Chrome), 4 pliki rejestr_*.xlsx -> inbox/ (cdn.um.warszawa.pl); "+" w URL to spacja w nazwie pliku
- Raport za poprzedni miesiąc -> mail do krzysiekdc@gmail.com + raport-<miesiąc>.md

## 3. Inwestycje Ursus (automaty/inwestycje_runner.py + instrukcja.md)

- Instrukcja: automaty/instrukcja.md (lokalna kopia z Drive "Ursus - inwestycje - instrukcja dla Vibe CLI"; token Apify WYCIĘTY - tylko zmienna środowiskowa APIFY_TOKEN)
- Wynik: Google Doc "Ursus - inwestycje - <miesiąc> <rok>" w folderze Drive 0AIt2XYCG5wG1Uk9PVA
- Współdzielenie z rejestrami: share_registers() kopiuje XLSX z rejestry-urbanistyczne/inbox; Vibe nie pobiera ponownie WZ/PnB, tylko brakujące LCP/ZRID/zgłoszenia; może użyć raportu raport-<miesiąc>.md z automatu rejestrów

## Jak dodać kolejny automat

1. Nowy folder + runner wg wzoru automaty/rejestry_runner.py (state.json, .daemon.lock, runner.log, runs/)
2. Task w Harmonogramie z XML: LogonTrigger + opcjonalny CalendarTrigger (rejestracja w root wymaga elewacji/UAC; modyfikacja własnych tasków działa bez)
3. Prompt lokalnie lub w .vibe; runner dokleja nagłówek kontekstu (miesiąc, ścieżki, wymóg RESULT: OK/FAIL)
