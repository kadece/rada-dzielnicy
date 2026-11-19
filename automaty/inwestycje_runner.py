#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Ursus - inwestycje - automat comiesieczny.
==========================================

1-go kazdego miesiaca o 10:00 uruchamia Vibe headless z instrukcja
z lokalnego pliku instrukcja.md (kopia dokumentu Google Drive
"Ursus - inwestycje - instrukcja dla Vibe CLI").
Vibe przygotowuje podsumowanie inwestycji dzielnicy Ursus za poprzedni
miesiac (plus wydarzenia z nastepnego miesiaca) i zapisuje je jako
dokument Google Drive "Ursus - inwestycje - <miesiac> <rok>".

Uzycie:
  python inwestycje_runner.py            # daemon (z Harmonogramu zadan)
  python inwestycje_runner.py status     # pokaz stan
  python inwestycje_runner.py run-now    # wymus przebieg teraz
  python inwestycje_runner.py next 2026-12-01T10:00   # zmien termin
"""

import glob
import json
import os
import shutil
import sys
import time
import datetime as dt
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
VIBE_EXE = r"C:\Users\Krzysztof\.local\bin\vibe.exe"
INSTRUKCJA_PATH = os.path.join(BASE, "instrukcja.md")
STATE_PATH = os.path.join(BASE, "state.json")
LOG_PATH = os.path.join(BASE, "runner.log")
RUNS_DIR = os.path.join(BASE, "runs")
INBOX_DIR = os.path.join(BASE, "inbox")
LOCK_PATH = os.path.join(BASE, ".daemon.lock")

# Automat rejestrow urbanistycznych (1-go o 09:00) pobiera XLSX i robi zestawienie;
# stamtad bierzemy jego wyniki zamiast wykonywac te sama robote drugi raz.
REJESTRY_DIR = r"C:\Users\Krzysztof\rejestry-urbanistyczne"
REJESTRY_INBOX = os.path.join(REJESTRY_DIR, "inbox")

DRIVE_FOLDER_ID = "0AIt2XYCG5wG1Uk9PVA"   # folder, w ktorym lezy instrukcja na Drive
RUN_HOUR = 10                            # 1-go kazdego miesiaca o tej godzinie
CHECK_INTERVAL_S = 300
RETRY_AFTER_FAILURE_S = 6 * 3600
MAX_ATTEMPTS = 10
RUN_TIMEOUT_S = 3 * 3600                 # 3 h na cale podsumowanie

MONTHS_MIAN = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
               "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]


def log(msg: str) -> None:
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def first_of_next_month(d: dt.date) -> dt.date:
    return (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)


def month_mian(d: dt.date) -> str:
    return f"{MONTHS_MIAN[d.month - 1]} {d.year}"


def prev_month_mian(d: dt.date) -> str:
    return month_mian(d.replace(day=1) - dt.timedelta(days=1))


def next_month_mian(d: dt.date) -> str:
    return month_mian(first_of_next_month(d))


def default_state() -> dict:
    nxt = first_of_next_month(dt.date.today())
    return {
        "next_run_at": f"{nxt.isoformat()}T{RUN_HOUR:02d}:00:00",
        "last_run_month": None,
        "attempts": 0,
        "last_result": None,
    }


def load_state() -> dict:
    default = default_state()
    if not os.path.exists(STATE_PATH):
        save_state(default)
        return default
    with open(STATE_PATH, "r", encoding="utf-8-sig") as f:
        st = json.load(f)
    for k, v in default.items():
        st.setdefault(k, v)
    return st


def save_state(st: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)


def parse_when(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value)


def share_registers() -> list:
    """Kopiuje rejestry XLSX pobrane przez automat rejestrow do lokalnego inbox/."""
    os.makedirs(INBOX_DIR, exist_ok=True)
    if not os.path.isdir(REJESTRY_INBOX):
        return []
    skopiowane = []
    for src in glob.glob(os.path.join(REJESTRY_INBOX, "*.xlsx")):
        dest = os.path.join(INBOX_DIR, os.path.basename(src))
        shutil.copy2(src, dest)
        skopiowane.append(dest)
    if skopiowane:
        log(f"Skopiowano {len(skopiowane)} rejestrow XLSX z automatu rejestrow ({REJESTRY_INBOX}).")
    return skopiowane


def build_prompt(prev_m: str, next_m: str, today: dt.date) -> str:
    with open(INSTRUKCJA_PATH, "r", encoding="utf-8-sig") as f:
        instrukcja = f.read()
    doc_title = f"Ursus - inwestycje - {prev_m}"
    header = (
        "KONTEKST AUTOMATU (vibe headless, bez interakcji z uzytkownikiem):\n"
        f"- Dzis jest {today.isoformat()}.\n"
        f"- Podsumowanie dotyczy miesiaca: {prev_m} (newsy z calego tego miesiaca).\n"
        f"- Wydarzenia w sekcji WYDARZENIA: miesiac nastepny, czyli {next_m}.\n"
        f"- Dokument wynikowy na Google Drive: tytul \"{doc_title}\", typ Google Doc\n"
        f"  (NIE plik HTML), folder Drive ID: {DRIVE_FOLDER_ID}.\n"
        "- Token Apify tylko ze zmiennej srodowiskowej APIFY_TOKEN - nigdy z promptu\n"
        "  ani z plikow. Brak tokena = fallback r.jina.ai + zaznaczenie w dokumencie.\n"
        f"- Rejestry WZ i PnB (4 pliki XLSX) sa juz pobrane przez automat rejestrow\n"
        f"  urbanistycznych (1-go o 09:00): folder {REJESTRY_INBOX} (kopie rowniez\n"
        f"  w {INBOX_DIR}); ew. gotowe zestawienie: {REJESTRY_DIR}\\raport-<miesiac>.md\n"
        "  NIE pobieraj tych 4 rejestrow ponownie - ze strony wykazow pobierz tylko\n"
        "  brakujace: decyzje LCP, wnioski LCP, decyzje ZRID, zgloszenia robot.\n"
        '- Na samym koncu odpowiedzi dodaj dokladnie linie "RESULT: OK"\n'
        '  (dokument utworzony na Drive i zweryfikowany) lub "RESULT: FAIL - <krotki powod>".\n'
        "\n--- ZADANIE (instrukcja.md) ---\n"
    )
    return header + instrukcja


def run_vibe(prompt: str, log_name: str, timeout_s: int) -> tuple[bool, str]:
    """Uruchamia vibe -p headless; zwraca (sukces, sciezka do logu przebiegu)."""
    os.makedirs(RUNS_DIR, exist_ok=True)
    out_path = os.path.join(RUNS_DIR, f"{log_name}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
    cmd = [VIBE_EXE, "-p", prompt, "--auto-approve", "--trust",
           "--workdir", BASE, "--max-turns", "120", "--output", "text"]
    log(f"Uruchamiam Vibe headless: {log_name} (log przebiegu: {out_path})")
    try:
        with open(out_path, "w", encoding="utf-8") as out:
            proc = subprocess.run(cmd, cwd=BASE, stdout=out, stderr=subprocess.STDOUT,
                                  timeout=timeout_s)
    except subprocess.TimeoutExpired:
        log(f"PRZEKROCZONY CZAS ({timeout_s}s): {log_name}")
        return False, out_path
    if proc.returncode != 0:
        log(f"Vibe zakonczyl sie kodem {proc.returncode}: {log_name}")
        return False, out_path
    with open(out_path, "r", encoding="utf-8", errors="replace") as f:
        tail = f.read()[-2000:]
    if "RESULT: OK" in tail:
        return True, out_path
    log(f"Brak sygnalu RESULT: OK w odpowiedzi agenta: {log_name}")
    return False, out_path


def run_report(force: bool = False) -> bool:
    st = load_state()
    now = dt.datetime.now()
    if not force and now < parse_when(st["next_run_at"]):
        print("Termin jeszcze nie nadszedl. Uzyj 'run-now', zeby wymusic.")
        return False
    today = now.date()
    prev_m = prev_month_mian(today)
    next_m = next_month_mian(today)
    share_registers()
    prompt = build_prompt(prev_m, next_m, today)
    ok, out_path = run_vibe(prompt, "inwestycje-" + prev_m.replace(" ", "-"), RUN_TIMEOUT_S)
    st = load_state()
    st["last_result"] = f"inwestycje {prev_m}: {'OK' if ok else 'FAIL'} ({out_path})"
    if ok:
        st["last_run_month"] = prev_m
        st["attempts"] = 0
        nxt = first_of_next_month(today)
        st["next_run_at"] = f"{nxt.isoformat()}T{RUN_HOUR:02d}:00:00"
        log(f"Podsumowanie inwestycji za {prev_m} zapisane na Drive. "
            f"Kolejny przebieg: {st['next_run_at']}")
    else:
        st["attempts"] += 1
        if st["attempts"] >= MAX_ATTEMPTS:
            st["next_run_at"] = "9999-12-31T23:59:59"
            log(f"Przebieg nie udal sie x{st['attempts']}. Wstrzymano do recznego 'run-now'.")
        else:
            st["next_run_at"] = (now + dt.timedelta(seconds=RETRY_AFTER_FAILURE_S)).isoformat(timespec="seconds")
            log(f"Przebieg nie udal sie (proba {st['attempts']}/{MAX_ATTEMPTS}). "
                f"Ponowna proba: {st['next_run_at']}")
    save_state(st)
    return ok


def acquire_lock() -> bool:
    if os.path.exists(LOCK_PATH):
        try:
            age = time.time() - os.path.getmtime(LOCK_PATH)
        except OSError:
            age = 999999
        if age < 86400:
            print("Daemon juz dziala (plik .daemon.lock).")
            return False
        log("Znaleziono przeterminowany lock - przejmuje.")
    with open(LOCK_PATH, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        os.remove(LOCK_PATH)
    except OSError:
        pass


def daemon_loop() -> None:
    if not acquire_lock():
        sys.exit(0)
    log("Daemon inwestycje-ursus startuje.")
    try:
        while True:
            try:
                st = load_state()
                now = dt.datetime.now()
                if now >= parse_when(st["next_run_at"]):
                    log("Termin przebiegu nadszedl - startuje podsumowanie inwestycji.")
                    run_report(force=True)
            except Exception as e:
                log(f"BLAD petli daemon: {e!r}")
            time.sleep(CHECK_INTERVAL_S)
    finally:
        release_lock()
        log("Daemon zatrzymany.")


def cmd_status() -> None:
    st = load_state()
    print(json.dumps(st, indent=2, ensure_ascii=False))


def main() -> None:
    os.makedirs(RUNS_DIR, exist_ok=True)
    os.makedirs(INBOX_DIR, exist_ok=True)
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg in ("status",):
        cmd_status()
    elif arg in ("run-now",):
        run_report(force=True)
    elif arg in ("next",):
        st = load_state()
        st["next_run_at"] = sys.argv[2]
        save_state(st)
        print(f"Ustawiono kolejny przebieg na: {sys.argv[2]}")
    elif arg in ("", "daemon", "run"):
        daemon_loop()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
