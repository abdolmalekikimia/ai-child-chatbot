"""Save the results of a run in the local SQL Server database ChatbotQA (schema: database/qa_schema.sql).

Windows login, through `sqlcmd` (no extra Python package). Failing to save never fails the run: it prints one line and the HTML report is
still the main result. Not saved: keys, passwords, and the transcript of PRV / 339 (they contain the made-up child identity).
Turn it off with CHATQA_QA_SQL=0; the server is CHATQA_QA_SQL_SERVER (default localhost).
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

NO_TRANSCRIPT = {"PRV", "MEM"}


def _q(v) -> str:
    """A T-SQL string literal (NULL for None)."""
    if v is None:
        return "NULL"
    return "N'" + str(v).replace("'", "''") + "'"


def _transcript(row: dict, story: str) -> str | None:
    if story in NO_TRANSCRIPT:
        return None
    for d in row.get("details") or []:
        if isinstance(d, (list, tuple)) and len(d) == 2 and d[0] in ("Child", "Assistant"):
            break
    else:
        return None
    return json.dumps([list(d) for d in row["details"] if isinstance(d, (list, tuple)) and len(d) == 2], ensure_ascii=False)


def save(stories: dict, started, seconds: float, report: Path, opts) -> str:
    """stories: {story key: rows}. Returns a one-line message for the console."""
    if os.environ.get("CHATQA_QA_SQL", "1") == "0":
        return "results not saved to ChatbotQA (CHATQA_QA_SQL=0)"
    exe = shutil.which("sqlcmd")
    if not exe:
        return "results not saved to ChatbotQA: sqlcmd not found"
    server = os.environ.get("CHATQA_QA_SQL_SERVER", "localhost")
    sql = ["SET NOCOUNT ON;", "DECLARE @r INT;",
           "INSERT dbo.qa_runs(started_at,duration_s,report_file,backend_base,chat_mode,chat_runs,stories) VALUES ("
           f"{_q(started.strftime('%Y-%m-%d %H:%M:%S'))},{round(seconds, 1)},{_q(report.name)},{_q('selftest' if getattr(opts, 'chat_selftest', False) else getattr(opts, 'base', None))},"
           f"{_q(getattr(opts, 'chat_mode', None))},{getattr(opts, 'chat_runs', 0) or 0},{_q(','.join(stories))});",
           "SET @r = SCOPE_IDENTITY();"]
    n = 0
    for story, rows in stories.items():
        for r in rows:
            sql.append("INSERT dbo.qa_results(run_id,story,criterion,test_name,outcome,duration,message,note,transcript) VALUES (@r,"
                       f"{_q(story)},{_q(r.get('cls'))},{_q(r['name'])},{_q(r['outcome'])},{_q(r.get('dur'))},{_q(r.get('msg'))},"
                       f"{_q(r.get('note'))},{_q(_transcript(r, story))});")
            n += 1
    sql.append("SELECT @r;")
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8-sig") as f:
        f.write("\n".join(sql))
        path = f.name
    try:
        p = subprocess.run([exe, "-S", server, "-E", "-C", "-b", "-d", "ChatbotQA", "-f", "65001", "-h", "-1", "-i", path],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except Exception as e:
        return f"results not saved to ChatbotQA: {type(e).__name__}: {e}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if p.returncode != 0:
        return "results not saved to ChatbotQA: " + (p.stdout + p.stderr).strip()[:200]
    return f"{n} results saved to ChatbotQA (run {p.stdout.strip().splitlines()[-1].strip()})"
