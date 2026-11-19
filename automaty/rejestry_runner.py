#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Rejestry urbanistyczne Ursus - automat comiesieczny.
====================================================

1-go kazdego miesiaca o 09:00 uruchamia Vibe headless z promptem
z pliku C:\Users\Krzysztof\.vibe\zadanie_rejestry_urbanistyczne.txt.
Vibe przygotowuje raport z rejestrow urbanistycznych Dzielnicy Ursus
za poprzedni miesiac kalendarzowy i wysyla go mailem do Krzysztofa.

Pliki XLSX z rejestrami Krzysztof wrzuca recznie do folderu inbox/
(pobiera je ze strony Urzedu Dzielnicy Ursus, ktora blokuje automaty).

Uzycie:
  python rejestry_runner.py            # daemon (do uruchamiania z Harmonogramu zadan)
  python rejestry_runner.py status     # pokaz stan
  python rejestry_runner.py run-now    # wymus przebieg teraz
  python rejestry_runner.py next 2026-12-01T09:00   # zmien termin kolejnego przebiegu
"""

import json
import os
import re
import sys
import time
import datetime as dt
import subprocess
import urllib.request
from urllib.parse import urljoin

BASE = os.path.dirname(os.path.abspath(__file__))
VIBE_EXE = r"C:\Users\Krzysztof\.local\bin\vibe.exe"
USER_PROMPT_PATH = r"C:\Users\Krzysztof\.vibe\zadanie_rejestry_urbanistyczne.txt"
WYKAZY_URL = "https://ursus.um.warszawa.pl/-/wykazy-za-rok-2026"
HTTP_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}
REJESTRY_PATTERNS = (
    "rejestr_dec_wz",
    "rejestr_wnioskow_o_wz",
    "rejestr_wnioskow_o_pozw_na_bud",
    "rejestr_decyzji_o_pozw_na_bud",
)
STATE_PATH = os.path.join(BASE, "state.json")
LOG_PATH = os.path.join(BASE, "runner.log")
RUNS_DIR = os.path.join(BASE, "runs")
INBOX_DIR = os.path.join(BASE, "inbox")
LOCK_PATH = os.path.join(BASE, ".daemon.lock")

RECIPIENT = "krzysiekdc@gmail.com"
RUN_HOUR = 9                      # 1-go kazdego miesiaca o tej godzinie
CHECK_INTERVAL_S = 300            # co ile sekund daemon sprawdza termin
RETRY_AFTER_FAILURE_S = 6 * 3600  # co ile ponawiac nieudany przebieg
MAX_ATTEMPTS = 10                 # po tylu porazkach czeka na reczne "run-now"
RUN_TIMEOUT_S = 5400              # 90 min na przygotowanie raportu

MONTHS_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
             "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]


def log(msg: str) -> None:
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def first_of_next_month(d: dt.date) -> dt.date:
    return (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)


def prev_month_label(d: dt.date) -> str:
    prev = d.replace(day=1) - dt.timedelta(days=1)
    return f"{MONTHS_PL[prev.month - 1]} {prev.year}"


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


def _http_get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=HTTP_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download_registers() -> list:
    """Pobiera 4 rejestry XLSX ze strony wykazow urzedu do inbox/. Zwraca liste sciezek."""
    os.makedirs(INBOX_DIR, exist_ok=True)
    html = _http_get(WYKAZY_URL).decode("utf-8", errors="replace")
    hrefs = [urljoin(WYKAZY_URL, h)
             for h in re.findall(r'href="([^"]*\.xlsx[^"]*)"', html, flags=re.IGNORECASE)]
    urls = []
    for pat in REJESTRY_PATTERNS:
        m = next((h for h in hrefs if pat in h.lower().replace("+", "_")), None)
        if m:
            urls.append(m)
    if len(urls) < len(REJESTRY_PATTERNS):
        log(f"Strona wykazow nie zawiera wszystkich rejestrow ({len(urls)}/{len(REJESTRY_PATTERNS)}).")
        return []
    pobrane = []
    for url in urls:
        seg = [s for s in url.split("/") if s]
        nazwa = next((s for s in reversed(seg) if s.lower().endswith(".xlsx")), seg[-1].split("?")[0])
        nazwa = nazwa.replace("+", " ")
        dest = os.path.join(INBOX_DIR, nazwa)
        data = _http_get(url)
        with open(dest, "wb") as f:
            f.write(data)
        log(f"Pobrano rejestr {nazwa} ({len(data)} B)")
        pobrane.append(dest)
    return pobrane


def build_prompt(month_label: str, today: dt.date) -> str:
    with open(USER_PROMPT_PATH, "r", encoding="utf-8-sig") as f:
        user_task = f.read()
    report_file = os.path.join(BASE, "raport-" + month_label.replace(" ", "-") + ".md")
    header = (
        "KONTEKST AUTOMATU (vibe headless, bez interakcji z uzytkownikiem):\n"
        f"- Dzis jest {today.isoformat()}.\n"
        f"- Raport dotyczy miesiaca: {month_label} (poprzedni miesiac kalendarzowy).\n"
        f"- Pliki XLSX z rejestrami (4 sztuki rejestr_*.xlsx) zostaly juz pobrane\n"
        f"  automatycznie do folderu: {INBOX_DIR} - uzyj ich; NIE pros o nie uzytkownika.\n"
        "  Zadanie ponizej moze wspominac o recznym pobieraniu plikow - ignoruj to.\n"
        '  Jesli mimo to ktoregos pliku brakuje: "RESULT: FAIL - brak pliku XLSX".\n'
        "- Wykonaj zadanie ponizej, ale raport wyslij MAILEM do\n"
        f"  {RECIPIENT} (subject: \"Raport rejestrow urbanistycznych Ursus - {month_label}\")\n"
        f"  oraz zapisz kopie raportu do pliku: {report_file}\n"
        "  Zadanie ponizej moze pisac o odpowiedzi \"w czacie\" - w tym trybie headless\n"
        "  zamiast tego wyslij raport mailem; czatu nikt nie czyta.\n"
        '- Na samym koncu odpowiedzi dodaj dokladnie linie "RESULT: OK"\n'
        '  (raport wyslany mailem i zapisany do pliku) lub "RESULT: FAIL - <krotki powod>".\n'
        "\n--- ZADANIE (plik uzytkownika: zadanie_rejestry_urbanistyczne.txt) ---\n"
    )
    return header + user_task


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
    month_label = prev_month_label(now.date())
    pobrane = download_registers()
    if not pobrane:
        st = load_state()
        st["last_result"] = f"rejestry {month_label}: FAIL (nie udalo sie pobrac XLSX ze strony wykazow)"
        st["attempts"] += 1
        if st["attempts"] >= MAX_ATTEMPTS:
            st["next_run_at"] = "9999-12-31T23:59:59"
            log(f"Pobieranie rejestrow nie udane x{st['attempts']}. Wstrzymano do recznego 'run-now'.")
        else:
            st["next_run_at"] = (now + dt.timedelta(seconds=RETRY_AFTER_FAILURE_S)).isoformat(timespec="seconds")
            log(f"Pobieranie rejestrow nie udane (proba {st['attempts']}/{MAX_ATTEMPTS}). "
                f"Ponowna proba: {st['next_run_at']}")
        save_state(st)
        return False
    prompt = build_prompt(month_label, now.date())
    ok, out_path = run_vibe(prompt, "rejestry-" + month_label.replace(" ", "-"), RUN_TIMEOUT_S)
    st = load_state()
    st["last_result"] = f"rejestry {month_label}: {'OK' if ok else 'FAIL'} ({out_path})"
    if ok:
        st["last_run_month"] = month_label
        st["attempts"] = 0
        nxt = first_of_next_month(now.date())
        st["next_run_at"] = f"{nxt.isoformat()}T{RUN_HOUR:02d}:00:00"
        log(f"Raport rejestrow urbanistycznych za {month_label} wyslany do {RECIPIENT}. "
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
    os.makedirs(INBOX_DIR, exist_ok=True)
    log("Daemon rejestrow urbanistycznych startuje.")
    try:
        while True:
            try:
                st = load_state()
                now = dt.datetime.now()
                if now >= parse_when(st["next_run_at"]):
                    log("Termin przebiegu nadszedl - startuje raport rejestrow.")
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
