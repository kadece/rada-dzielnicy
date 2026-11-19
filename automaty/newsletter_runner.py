#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BiZU Newsletter Home Server
==========================

Daemon planujacy cykl newslettera Stowarzyszenia Bezpieczny i Zielony Ursus (co 14 dni).

Co robi:
  - pilnuje terminu kolejnego przebiegu (state.json),
  - gdy termin nadejdzie (albo byl zalegly - np. po zaniku pradu), uruchamia
    Vibe headless ("vibe -p <prompt> --auto-approve --trust"), ktory:
      a) zbiera tematy z FB i zielonyursus.pl,
      b) wysyla Krzyśkowi maila z PROPOZYCJA tematow i zapisuje ja do pliku
         proposal-<N>.md  ->  faza "awaiting_approval",
  - po zatwierdzeniu ("finalize") Vibe przygotowuje i wysyla finalny
    newsletter WYLACZNIE do Krzyśka (on rozsyla dalej do czlonkow)
    i archiwizuje wydanie w folderze Drive newsletter-bizu.

Uzycie:
  python newsletter_runner.py            # daemon (petla, do uruchamiania z Harmonogramu zadan)
  python newsletter_runner.py status    # pokaz stan
  python newsletter_runner.py run-now   # wymus przebieg propozycji teraz
  python newsletter_runner.py finalize [korekty...]  # zatwierdzenie + ewentualne korekty
  python newsletter_runner.py next 2026-12-01T09:00   # zmien termin kolejnego przebiegu
"""

import json
import os
import sys
import time
import datetime as dt
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
VIBE_EXE = r"C:\Users\Krzysztof\.local\bin\vibe.exe"
STATE_PATH = os.path.join(BASE, "state.json")
LOG_PATH = os.path.join(BASE, "runner.log")
RUNS_DIR = os.path.join(BASE, "runs")
LOCK_PATH = os.path.join(BASE, ".daemon.lock")
PROPOSAL_PROMPT_PATH = os.path.join(BASE, "proposal_prompt.txt")
FINALIZE_PROMPT_PATH = os.path.join(BASE, "finalize_prompt.txt")

RECIPIENT = "krzysiekdc@gmail.com"
DRIVE_FOLDER_ID = "13aZilfHN8X8A3AzbReLOR1JFSj6y4zrb"
INTERVAL_DAYS = 14
CHECK_INTERVAL_S = 300          # co ile sekund daemon sprawdza termin
RETRY_AFTER_FAILURE_S = 6 * 3600  # co ile ponawiac nieudany przebieg
MAX_ATTEMPTS = 10              # po tylu porazkach czeka na reczne "run-now"
PROPOSAL_TIMEOUT_S = 5400       # 90 min na zbiorka tematow (odstepy 20 s przy r.jina.ai)
FINALIZE_TIMEOUT_S = 3600       # 60 min na finalny newsletter

MONTHS_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
             "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]


def log(msg: str) -> None:
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def load_state() -> dict:
    default = {
        "next_run_at": "2026-12-01T09:00:00",  # pierwszy przebieg nowego cyklu
        "issue": 2,                            # wydanie w przygotowaniu
        "phase": "idle",                       # idle | awaiting_approval
        "window": None,
        "proposal_file": None,
        "attempts": 0,
        "last_result": None,
    }
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


def window_for(run_date: dt.date, prev_send: dt.date) -> str:
    """Okno tematow: od dnia po poprzedniej wysylce do dnia wykonania przebiegu."""
    start = prev_send + dt.timedelta(days=1)
    end = run_date
    if start > end:
        start = end
    def d(x): return f"{x.day} {MONTHS_PL[x.month - 1]} {x.year}"
    if start == end:
        return d(start)
    if start.month == end.month and start.year == end.year:
        return f"{start.day}–{end.day} {MONTHS_PL[end.month - 1]} {end.year}"
    return f"{d(start)} – {d(end)}"


def fmt_ymd(x) -> str:
    return x.strftime("%Y-%m-%d")


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
    # Sukces rozpoznajemy po sygnale w finalnej odpowiedzi agenta.
    with open(out_path, "r", encoding="utf-8", errors="replace") as f:
        tail = f.read()[-2000:]
    if "RESULT: OK" in tail:
        return True, out_path
    log(f"Brak sygnalu RESULT: OK w odpowiedzi agenta: {log_name}")
    return False, out_path


def read_prompt(path: str, **kwargs) -> str:
    with open(path, "r", encoding="utf-8-sig") as f:
        tpl = f.read()
    return tpl.format(**kwargs)


def run_proposal(force: bool = False) -> bool:
    st = load_state()
    now = dt.datetime.now()
    if not force and now < parse_when(st["next_run_at"]):
        print("Termin jeszcze nie nadszedl. Uzyj 'run-now', zeby wymusic.")
        return False
    issue = st["issue"]
    today = now.date()
    prev_send = parse_when(st["next_run_at"]).date() - dt.timedelta(days=INTERVAL_DAYS)
    window = window_for(today, prev_send)
    proposal_file = os.path.join(BASE, f"proposal-{issue}.md")
    prompt = read_prompt(PROPOSAL_PROMPT_PATH,
                        ISSUE=issue, WINDOW=window, RECIPIENT=RECIPIENT,
                        PROPOSAL_FILE=proposal_file, DRIVE_FOLDER_ID=DRIVE_FOLDER_ID,
                        TODAY=fmt_ymd(today))
    ok, out_path = run_vibe(prompt, f"proposal-{issue}", PROPOSAL_TIMEOUT_S)
    st = load_state()
    st["last_result"] = f"proposal-{issue}: {'OK' if ok else 'FAIL'} ({out_path})"
    if ok:
        st["phase"] = "awaiting_approval"
        st["window"] = window
        st["proposal_file"] = proposal_file
        st["attempts"] = 0
        st["next_run_at"] = (now + dt.timedelta(days=INTERVAL_DAYS)).isoformat(timespec="seconds")
        log(f"Propozycja tematow wydania #{issue} (okno {window}) wyslana do {RECIPIENT}. "
            f"Czekam na zatwierdzenie; kolejny przebieg: {st['next_run_at']}")
    else:
        st["attempts"] += 1
        if st["attempts"] >= MAX_ATTEMPTS:
            st["next_run_at"] = "9999-12-31T23:59:59"  # czeka na reczne run-now
            log(f"Przebieg propozycji nie udal sie x{st['attempts']}. Wstrzymano do recznego 'run-now'.")
        else:
            st["next_run_at"] = (now + dt.timedelta(seconds=RETRY_AFTER_FAILURE_S)).isoformat(timespec="seconds")
            log(f"Przebieg propozycji nie udal sie (proba {st['attempts']}/{MAX_ATTEMPTS}). "
                f"Ponowna proba: {st['next_run_at']}")
    save_state(st)
    return ok


def run_finalize(corrections: str) -> bool:
    st = load_state()
    if st["phase"] != "awaiting_approval" or not st.get("proposal_file"):
        print("Nie ma propozycji oczekujacej na zatwierdzenie (phase != awaiting_approval).")
        return False
    if not os.path.exists(st["proposal_file"]):
        print(f"Brak pliku propozycji: {st['proposal_file']}")
        return False
    issue = st["issue"]
    window = st["window"] or window_for(
        dt.date.today(),
        parse_when(st["next_run_at"]).date() - dt.timedelta(days=INTERVAL_DAYS))
    prompt = read_prompt(FINALIZE_PROMPT_PATH,
                        ISSUE=issue, WINDOW=window, RECIPIENT=RECIPIENT,
                        PROPOSAL_FILE=st["proposal_file"],
                        CORRECTIONS=(corrections.strip() or "(brak korekt - temat zatwierdzony w calosci)"),
                        DRIVE_FOLDER_ID=DRIVE_FOLDER_ID,
                        TODAY=fmt_ymd(dt.date.today()))
    ok, out_path = run_vibe(prompt, f"finalize-{issue}", FINALIZE_TIMEOUT_S)
    st = load_state()
    st["last_result"] = f"finalize-{issue}: {'OK' if ok else 'FAIL'} ({out_path})"
    if ok:
        log(f"Finalny newsletter wydania #{issue} wyslany do {RECIPIENT} i zarchiwizowany w Drive.")
        st["phase"] = "idle"
        st["issue"] = issue + 1
        st["window"] = None
        st["proposal_file"] = None
        st["attempts"] = 0
    else:
        log(f"Finalizacja wydania #{issue} nie udala sie - sprobuj ponownie: "
            f"finalize {' '.join(sys.argv[2:]) if len(sys.argv) > 2 else ''}")
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
    log("Daemon BiZU newslettera startuje.")
    try:
        while True:
            try:
                st = load_state()
                now = dt.datetime.now()
                if st["phase"] != "awaiting_approval" and now >= parse_when(st["next_run_at"]):
                    log("Termin przebiegu nadszedl - startuje zbiorka tematow.")
                    run_proposal(force=True)
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
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg in ("status",):
        cmd_status()
    elif arg in ("run-now",):
        run_proposal(force=True)
    elif arg in ("finalize",):
        corrections = " ".join(sys.argv[2:])
        run_finalize(corrections)
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
