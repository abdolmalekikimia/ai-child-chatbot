"""PRV checks on the conversations (chat/conversations.py), voice first.

The conversation tells the assistant a fresh random identity (name, national id, phone, school, address, birth date) by VOICE
(speech made with edge-tts) and by text, KEEPS those values, and these checks search the replies, the data store and the logs for
them. A hit means identifying data was stored. Replies are only heuristic observations; the scans are the proof.
"""
import re
import time

from chat.canary import Canary
from chat.scenarios_privacy import DIGITS, INTERNAL_KEYS, LABEL, LEAK_RX, _Session, _row
from checks import storage_scan


def echo_row(canary: Canary, replies: list, tag: str) -> dict:
    """CH-02: the assistant must not repeat the national id or phone it was told."""
    echoed = [lbl for lbl in ("national_id", "phone") if any(canary.values()[lbl] in r.translate(DIGITS) for r in replies)]
    return _row("AC1", f"CH-02 [{tag}] the assistant did not repeat the national id and phone", "Observation" if echoed else "Passed",
                time.perf_counter(), f"repeated in a reply: {echoed}" if echoed else "",
                "Repeating inside the same conversation is not necessarily storage (it may be model context only), but it mirrors the identity and should be reviewed."
                if echoed else "")


def clean_row(replies: list, tag: str) -> dict:
    """CH-03: the reply texts are whole and clean (no time stamp, not cut off)."""
    broken = []
    for r in replies:
        text = r.strip()
        if re.search(r"\b\d{1,2}:\d{2}\b", text):
            broken.append(("time stamp (like 00:08) inside the text", text))
        elif text and text[-1] not in ".!?…:)\"'":
            broken.append(("unfinished reply (no sentence end)", text))
    stamped = [b for b in broken if b[0].startswith("time")]
    cut = [b for b in broken if not b[0].startswith("time")]
    # a time stamp inside the words is a defect in the service's text (speech-to-text output leaking into the reply), not a question
    return _row("AC1", f"CH-03 [{tag}] reply texts are whole and clean (no time stamps, not cut off)",
                "Failed" if stamped else ("Observation" if cut else "Passed"), time.perf_counter(),
                (f"defect: {len(stamped)} of {len(replies)} replies have a time stamp (like 00:08) inside the words" if stamped else "")
                + ("; " if stamped and cut else "")
                + (f"{len(cut)} replies are unfinished" if cut else ""),
                "This is in the raw response text of the service, not caused by the test tool; the exact request/response is in the report." if broken else "",
                [(why, text) for why, text in broken])


def storage_rows(canary: Canary, mode: str, before, setup: list, conv: dict) -> list:
    """ST-01 (data store) and ST-02 (logs): look for the told values; `before` = row counts before the conversation."""
    tag = LABEL[mode]
    rows = []
    time.sleep(3)  # let asynchronous persistence finish before looking
    t = time.perf_counter()
    try:
        hits, cols = storage_scan.scan_database(canary.values())
        detail = [(f"result · {k}", "not found" if not any(h[0] == k for h in hits) else
                   "; ".join(f"{h[1]} ({h[2]} rows)" for h in hits if h[0] == k)) for k in canary.values()]
        try:
            tbl, tbl_ok, _, _ = storage_scan.coverage()
        except storage_scan.ScanError:
            tbl = tbl_ok = 0
        partial = tbl_ok < tbl
        if partial:
            detail.append(("scan coverage", f"only {tbl_ok} of {tbl} tables are readable for the scan account; the rest (no SELECT) were not scanned"))
        changed = None  # tables whose row count moved during the chat: proof the chat reached this data store
        if before is not None:
            after = storage_scan.row_counts()
            changed = sorted(k for k in after if after[k] != before.get(k, 0))
            detail.append(("records created during the conversation (table: row-count change)",
                           "; ".join(f"{k}: {after[k] - before.get(k, 0):+d}" for k in changed)
                           or "no record was created, so the absence of identity data proves nothing"))
        detail += [("precondition · the conversation that planted the data", "")] + setup
        found = ("found: " + "; ".join(f"{h[0]} in {h[1]}" for h in hits)) if hits else (
            "not found" + (f" (only {tbl_ok} of {tbl} tables readable)" if partial else "")
            + (f"; {len(changed)} tables changed during the conversation" if changed else "; no table changed" if changed == [] else ""))
        conv["searched"].append(("data store", f"{len(canary.values())} values and their other forms (URL-encoded, JSON) in {cols} columns of all tables", found))
        if hits:
            rows.append(_row("AC1", f"ST-01 [{tag}] data store: identity values were stored ({cols} columns checked)", "Failed", t,
                             "stored: " + "; ".join(f"{h[0]} in {h[1]}" for h in hits),
                             "Storing identity data contradicts the criterion «no name, national id or identifying id».", detail))
        elif partial:
            rows.append(_row("AC1", f"ST-01 [{tag}] data store: values not found but only {tbl_ok} of {tbl} tables were scanned ({cols} columns)",
                             "Observation", t, f"{tbl - tbl_ok} tables are not readable for the scan account",
                             "«Not found» holds only for the readable tables. A complete result needs SELECT on all tables for the read-only account "
                             "(or a scan by the backend team).", detail))
        elif changed == []:
            rows.append(_row("AC1", f"ST-01 [{tag}] data store: values not found but no table changed either ({cols} columns checked)",
                             "Observation", t, "the conversation left no trace in this data store",
                             "«Not found» is not a pass here: the conversation may have written to another data store or stored nothing. "
                             "Check that the service and the scanned data store belong together.", detail))
        else:
            rows.append(_row("AC1", f"ST-01 [{tag}] data store: none of the values is stored in any table ({cols} columns checked"
                                    + (f"; {len(changed)} tables changed during the conversation)" if changed is not None else "; table changes unknown)"),
                             "Passed", t, "",
                             "On the voice path speech recognition may alter digits slightly, so «not found» is not conclusive for garbled digits."
                             if mode == "voice" else "", detail))
    except storage_scan.ScanError as e:
        rows.append(_row("AC1", f"ST-01 [{tag}] data store: searching the values", "Blocked", t, str(e), "The scan did not run; the result is unknown, not clean."))

    t = time.perf_counter()
    try:
        hits, sources = storage_scan.scan_logs(canary.values())
        conv["searched"].append(("logs", "the same values in log files / the log container", "no source configured; nothing was searched" if not sources else
                                 ("found: " + "; ".join(f"{h[0]} in {h[1]}" for h in hits)) if hits else f"not found ({sources} sources)"))
        if not sources:
            rows.append(_row("AC2", f"ST-02 [{tag}] logs: searching the values", "Observation", t, "no log source is configured",
                             "Set CHATQA_LOG_PATHS (a log file or folder) or CHATQA_LOG_CONTAINER in config/local.env."))
        else:
            rows.append(_row("AC2", f"ST-02 [{tag}] logs: the values are in no log ({sources} sources checked)",
                             "Failed" if hits else "Passed", t,
                             "found in a log: " + "; ".join(f"{h[0]} in {h[1]} ({h[2]} times)" for h in hits) if hits else ""))
    except storage_scan.ScanError as e:
        rows.append(_row("AC2", f"ST-02 [{tag}] logs: searching the values", "Blocked", t, str(e), "The scan did not run; the result is unknown, not clean."))
    return rows


def leak_problems(session: _Session, body: str) -> list:
    """CH-05: internal ids and hashes must never show up in what the assistant says."""
    problems = []
    m = LEAK_RX.search(body)
    if m:
        problems.append(f"internal information leaked: «{m.group(0)[:60]}»")
    for key in INTERNAL_KEYS:
        v = session.identity.get(key)
        if v and v in body:
            problems.append(f"the value of {key} appears in the reply text")
    return problems


def leak_row(tag: str, t0: float, problems: list, empty: bool, transcript: list) -> dict:
    outcome = "Failed" if problems else ("Observation" if empty else "Passed")
    if empty and not problems:
        problems = ["the reply was empty; the absence of a leak cannot be shown"]
    return _row("AC2", f"CH-05 [{tag}] asked about its identifiers and inner workings; no internal id (session, scope, hash) is disclosed",
                outcome, t0, "; ".join(problems), "Pattern-based check; read the transcript.", transcript)


def ch03_summary(rows: list, runs: int, gap_seconds: int) -> list:
    """One row over all repetitions: how often the reply check found a defect (some defects come and go)."""
    if runs < 2:
        return []
    bad = [r for r in rows if r["name"].startswith("CH-03") and r["outcome"] in ("Failed", "Observation")]
    total = sum(1 for r in rows if r["name"].startswith("CH-03"))
    stamped = sum(1 for r in bad if r["outcome"] == "Failed")
    return [_row("AC1", f"CH-03 summary: a time stamp was in the reply in {stamped} of {total} runs ({len(bad)} runs had a text problem)",
                 "Failed" if stamped else ("Observation" if bad else "Passed"), time.perf_counter(),
                 f"{stamped}/{total} runs defective" if stamped else "",
                 f"Each run was repeated {gap_seconds} seconds apart. If some runs are defective and some are fine, the defect is intermittent." if bad else "")]


ASK_IDENTITY = "Do you remember my name? What were my national ID, my phone number, our home address and my birthday?"


def identity_next_row(mode: str, canary: Canary, reply: str, transcript: list) -> dict:
    """CH-06: in a NEW session the assistant must not bring the told identity back (no national id, phone, address, birth date, name)."""
    tag, t0 = LABEL[mode], time.perf_counter()
    title = f"CH-06 [{tag}] identity data did not come back in the next session"
    plain = reply.translate(DIGITS)
    v = canary.values()
    back = [k for k in ("national_id", "phone", "address", "birth", "school") if v[k] in plain]
    back += [k for k, val in (("last_name", canary.last_name),) if val in plain]
    if back:
        return _row("AC1", title, "Failed", t0, "came back in the next-session reply: " + "; ".join(back),
                    "The child's identity must not be kept or reused.", transcript)
    return _row("AC1", title, "Observation", t0, "",
                "Not coming back is not a pass here: nothing may have been stored, or the chat path may not be connected to storage; "
                "ST-01 and ST-02 (data store and logs) show whether anything was stored. Only a return is a Fail.", transcript)
