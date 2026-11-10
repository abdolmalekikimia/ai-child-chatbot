"""PRV: privacy of a synthetic child identity (nothing identifying is stored or leaked).

A fresh random synthetic identity (name, national id, phone, school, address, birth date) is told to the assistant by voice and text. The
checks: it is not repeated back, internal identifiers do not leak into replies, it does not come back in a new session, and a read-only
scan of the QA data store and the service logs does not find it. The scanner proves itself first on a scratch database.
"""
import time

from checks import storage_scan
from core.models import Story
from stories._common import chat_rows

KEY = "PRV"

CRITERIA = [
    ("AC1", "The child record is created without a name, national id or identifying id", []),
    ("AC2", "The child identifier does not reach the model, telemetry or logs", []),
]


def _scanner_selfcheck_row() -> dict:
    """The privacy scans are only trustworthy if the scanner can find a planted value: prove it on a scratch database."""
    t0 = time.perf_counter()
    row = {"cls": "Scen-AC1", "name": "ST-00 the data-store scanner works (positive and negative control on a scratch database)",
           "dur": "", "msg": "", "note": "", "details": []}
    try:
        row.update(outcome="Passed", note=storage_scan.scanner_selfcheck())
    except AssertionError as e:
        row.update(outcome="Failed", msg=str(e), note="The scanner is not trustworthy; do not accept the ST-01 result.")
    except storage_scan.ScanError as e:
        row.update(outcome="Blocked", msg=str(e), note="The data store or its container is not available; the storage scans do not run.")
    row["dur"] = f"{time.perf_counter() - t0:.1f}s"
    return row


def run(options) -> Story:
    story = Story(KEY, "PRV", "Privacy of a synthetic child identity", CRITERIA)
    story.rows += chat_rows(options, KEY, story.conversations)
    check = _scanner_selfcheck_row()  # shown only if the scanner is untrustworthy or could not run
    if check["outcome"] != "Passed":
        story.rows.append(check)
    story.checks.append((
        "Stable pseudonymous child identifier: generation, storage and retrieval", "not_checked",
        "Not built in the reference system and the requirement is still open; until it is defined this is not tested and is not a failure. "
        "A chat client also cannot see the stored child record, so this needs a different test level."))
    return story
