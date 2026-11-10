"""One entry point for the whole QA run.

  py run_qa.py                         # FULL run: every scenario group, ONE combined HTML report
  py run_qa.py --task PRV              # focused run for one scenario group (repeatable); report named after the group
  py run_qa.py --list                  # coverage catalog: which groups exist and what they depend on
  py run_qa.py --base https://<test-env>   # talk to a live system under test (otherwise nothing is exercised)
  py run_qa.py --chat-mode voice       # voice only (default: voice first, then text)
  py run_qa.py --chat-selftest         # run the scenarios against a built-in fake server (checks the checks)
  py run_qa.py --no-open               # do not open the browser

If the conversation with the assistant did not run for a requested mode, the tool prints an ERROR, writes NO report and saves nothing
(exit code 3). The HTML report is rewritten after each group, so an interrupted run still leaves a partial report.
"""
import argparse
import os
import sys
import webbrowser
from datetime import datetime

from chat.conversations import modes_for, run_central
from chat.scenarios_privacy import LABEL
from config import settings
from config.catalog import GROUPS, find
from config.settings import REPORTS_DIR
from core import qa_db
from core.report_html import build_report
from stories import story_memory, story_onboarding, story_privacy, story_safety

STORIES = {"SAF": story_safety, "PRV": story_privacy, "MEM": story_memory, "ONB": story_onboarding}

PROVENANCE = (
    "Each row is an automated check on a real conversation with the assistant (voice or text) or a check of storage. "
    "BLOCKED means the check did not run (for example the environment was not reachable); it never counts as a pass. "
    "OBSERVATION means the transcript must be read; it is not a confirmed defect. "
    "NOT BUILT means the check is not built yet or depends on something outside this repository."
)


def print_catalog() -> None:
    print(f"{'Group':<7}{'Modes':<34}{'Status':<13}Dependency")
    for g in GROUPS:
        print(f"{g.key:<7}{g.modes:<34}{g.status:<13}{g.dependency_status}")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # non-ASCII text must not crash a cp1252 console
        stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", action="append", help="scenario group to run: SAF, PRV, MEM or ONB (repeatable)")
    ap.add_argument("--list", action="store_true", help="print the coverage catalog and exit")
    ap.add_argument("--base", default=settings.BASE_URL or None, help="base URL of the system under test")
    ap.add_argument("--chat-mode", choices=["both", "voice", "text"], default="both", help="voice first, then text")
    ap.add_argument("--chat-runs", type=int, default=3, help="repeat the conversations this many times (default 3)")
    ap.add_argument("--chat-gap", type=int, default=60, help="seconds between runs (default 60)")
    ap.add_argument("--chat-selftest", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    opts = ap.parse_args()

    if opts.list:
        print_catalog()
        return 0

    if opts.task:
        keys = []
        for ref in opts.task:
            group = find(ref)
            if group is None:
                print(f"Unknown group: {ref}. Known: {', '.join(g.key for g in GROUPS)}")
                return 2
            keys.append(group.key)
    else:
        keys = sorted(STORIES)

    full = not opts.task
    REPORTS_DIR.mkdir(exist_ok=True)
    started = datetime.now()
    name = "QA_Full" if full else "_".join(keys)
    report = REPORTS_DIR / f"{name}_Report_{started:%Y%m%d_%H%M%S}.html"
    settings.AUDIO_DIR = settings.AUDIO_ROOT / report.stem   # voice clips: same name as the report, own folder
    title = "AI Child Chatbot QA Report" if full else " + ".join(keys) + " QA Report"

    def write(done: list, partial: bool) -> None:
        html_text = build_report(done, started, (datetime.now() - started).total_seconds(), title=title,
                                 footer="AI Child Chatbot QA", provenance=PROVENANCE, catalog=list(GROUPS) if full else None,
                                 partial=partial)
        report.write_text(html_text, encoding="utf-8")

    stories = []
    try:
        print("\n[conversations] each scenario group has its own conversations ...", flush=True)
        opts.stories = tuple(keys)
        opts.central = run_central(opts)  # None without --base / --chat-selftest
        if opts.central is not None:  # a conversation that did not run is an error, not a report: both voice and text must be there
            missing = [(k, LABEL[m]) for k in keys for m in modes_for(k, opts)
                       if not any(cv["mode"] == LABEL[m] for cv in opts.central.conversations[k])]
            if missing:
                print("\nERROR: the conversation with the assistant did not run, so no report was written:")
                for k, tag in missing:
                    why = next((r["msg"] for r in opts.central.rows[k] if r["outcome"] == "Blocked" and r.get("msg")), "no answer from the environment")
                    print(f"   {k} [{tag}]: {why}")
                print("   Check that the test environment is reachable and run again. Nothing was saved.")
                return 3
        for n, key in enumerate(keys, 1):
            print(f"\n[{n}/{len(keys)}] {key} ...", flush=True)
            stories.append(STORIES[key].run(opts))
            write(stories, partial=n < len(keys))  # the report is updated after every group
            print(f"   report updated: {report}", flush=True)
    except KeyboardInterrupt:
        if stories:
            write(stories, partial=True)
            print(f"\nINTERRUPTED: partial report kept: {report}")
        return 130
    print(f"\nreport: {report}")
    try:
        print("   " + qa_db.save({k: st.rows for k, st in zip(keys, stories)}, started, (datetime.now() - started).total_seconds(), report, opts), flush=True)
    except Exception as e:  # saving must never break a run
        print(f"   results not saved to the results database: {type(e).__name__}: {e}", flush=True)
    if not opts.no_open:
        webbrowser.open(report.as_uri())
    return 1 if any(r["outcome"] == "Failed" for st in stories for r in st.rows) else 0


if __name__ == "__main__":
    sys.exit(main())
