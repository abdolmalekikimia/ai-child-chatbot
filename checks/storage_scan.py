"""Looks for canary values in the local database and in logs. Read-only; talks to PostgreSQL through `docker exec`.

The scanner is only worth trusting if it can find something, so `scanner_selfcheck()` plants a canary in a scratch
database (dropped afterwards) and proves the scan sees it, and sees nothing for a different random canary.
"""
import json
import subprocess
import urllib.parse
from pathlib import Path

from chat.canary import Canary
from config import settings
from config.settings import DB_CA_FILE, DB_CONTAINER, DB_NAME, DB_REMOTE, DB_REMOTE_ON, LOG_CONTAINER, LOG_PATHS

SCRATCH_DB = "qa_scan_selfcheck"


class ScanError(Exception):
    """The scan itself could not run (Docker off, container missing...). The result is unknown, not clean."""


def variants(value: str) -> list:
    """The same value as a store or log may hold it: plain, URL-encoded, JSON \\u-escaped."""
    out = {value, urllib.parse.quote(value), json.dumps(value)[1:-1]}
    return sorted(v for v in out if v)


def _sql_str(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def _check_pinned_db_cert() -> None:
    """If the data store sends only its own certificate (no CA in the chain), libpq cannot verify it against a CA.
    Pin instead: the certificate presented must be byte-identical to the file in CHATQA_DB_CA_FILE."""
    import socket
    import ssl
    import struct
    pinned = ssl.PEM_cert_to_DER_cert(DB_CA_FILE.read_text(encoding="ascii"))
    try:
        with socket.create_connection((DB_REMOTE["host"], int(DB_REMOTE["port"] or 5432)), 15) as raw:
            raw.sendall(struct.pack("!II", 8, 80877103))  # PostgreSQL SSLRequest
            if raw.recv(1) != b"S":
                raise ScanError("QA data store does not offer TLS")
            with ssl._create_unverified_context().wrap_socket(raw, server_hostname=DB_REMOTE["host"]) as tls:
                presented = tls.getpeercert(True)
    except OSError as e:
        raise ScanError(f"QA data store: {type(e).__name__}: {e}") from e
    if presented != pinned:
        raise ScanError("QA data store certificate differs from the pinned one (config/certs); re-pin only if the certificate was legitimately renewed")


def _psql_remote(sql: str) -> list:
    """Run one read-only query on the QA data store (TLS verify-full against the pinned certificate)."""
    sslmode = DB_REMOTE["sslmode"]
    if DB_CA_FILE:
        _check_pinned_db_cert()
        sslmode = "require"  # identity already proven by the exact-certificate pin above
    try:
        import psycopg
    except ImportError as e:
        raise ScanError("psycopg missing; run: pip install -r requirements.txt inside the project venv") from e
    try:
        with psycopg.connect(host=DB_REMOTE["host"], port=int(DB_REMOTE["port"] or 5432), dbname=DB_NAME,
                             user=DB_REMOTE["user"], password=DB_REMOTE["password"], sslmode=sslmode, connect_timeout=15) as conn:
            conn.read_only = True
            with conn.cursor() as cur:
                cur.execute(sql)
                return [[("" if v is None else str(v)) for v in row] for row in cur.fetchall()]
    except Exception as e:
        raise ScanError(f"QA data store: {type(e).__name__}: {str(e).strip()[:250]}") from e


def _psql(sql: str, db: str) -> list:
    try:
        p = subprocess.run(["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", "postgres", "-d", db, "-At", "-F", "|",
                            "-v", "ON_ERROR_STOP=1", "-f", "-"],
                           input=sql, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ScanError(f"docker/psql not available: {e}") from e
    if p.returncode != 0:
        raise ScanError((p.stderr or p.stdout).strip()[:300] or f"psql exit {p.returncode}")
    return [line.split("|") for line in p.stdout.splitlines() if line]


def scan_database(values: dict, db: str = DB_NAME) -> tuple:
    """Search every column of every table for every variant of every value.

    Returns (hits, columns_scanned); a hit is (label, 'schema.table.column', row_count).
    """
    vals = ",".join(f"({_sql_str(label)},{_sql_str(v)})" for label, val in values.items() for v in variants(val))
    sql = f"""
WITH cols AS (
  SELECT c.table_schema s, c.table_name t, c.column_name c
  FROM information_schema.columns c
  JOIN information_schema.tables tb ON tb.table_schema = c.table_schema AND tb.table_name = c.table_name
  WHERE tb.table_type = 'BASE TABLE' AND c.table_schema NOT IN ('pg_catalog', 'information_schema') AND c.data_type <> 'bytea'),
vals(label, val) AS (VALUES {vals}),
hits AS (
  SELECT cols.s, cols.t, cols.c, vals.label,
         (xpath('/row/n/text()', query_to_xml(format('select count(*) as n from %I.%I where strpos(%I::text, %L) > 0',
                                                     cols.s, cols.t, cols.c, vals.val), false, true, '')))[1]::text::int AS n
  FROM cols CROSS JOIN vals)
SELECT label, s || '.' || t || '.' || c, n::text FROM hits WHERE n > 0
UNION ALL SELECT '#columns', count(*)::text, '0' FROM cols;
"""
    rows = _psql_remote(sql) if (DB_REMOTE_ON and db == DB_NAME) else _psql(sql, db)
    scanned = next((int(r[1]) for r in rows if r[0] == "#columns"), 0)
    hits = [(r[0], r[1], int(r[2])) for r in rows if r[0] != "#columns"]
    return hits, scanned


def coverage(db: str = DB_NAME) -> tuple:
    """(tables, readable_tables, columns, readable_columns): the account only scans what it may SELECT, so say how much that is."""
    sql = """
SELECT count(*), count(*) FILTER (WHERE has_table_privilege(c.oid, 'select')),
       coalesce(sum(c.relnatts), 0)::bigint,
       coalesce(sum(c.relnatts) FILTER (WHERE has_table_privilege(c.oid, 'select')), 0)::bigint
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema');"""
    rows = _psql_remote(sql) if (DB_REMOTE_ON and db == DB_NAME) else _psql(sql, db)
    return tuple(int(x) for x in rows[0])


def row_counts(db: str = DB_NAME) -> dict:
    """Rows per table; compared before and after a chat to prove the conversation reached this database at all."""
    sql = """
SELECT t.table_schema || '.' || t.table_name,
       (xpath('/row/n/text()', query_to_xml(format('select count(*) as n from %I.%I', t.table_schema, t.table_name), false, true, '')))[1]::text
FROM information_schema.tables t
WHERE t.table_type = 'BASE TABLE' AND t.table_schema NOT IN ('pg_catalog', 'information_schema');"""
    rows = _psql_remote(sql) if (DB_REMOTE_ON and db == DB_NAME) else _psql(sql, db)
    return {r[0]: int(r[1]) for r in rows}


def scan_logs(values: dict) -> tuple:
    """Search log files/folders (CHATQA_LOG_PATHS) and the backend's docker logs (CHATQA_LOG_CONTAINER).

    Returns (hits, sources_scanned); a hit is (label, source, count). With no source configured, sources_scanned is 0.
    """
    sources = []
    for raw in LOG_PATHS:
        p = Path(raw)
        sources += [f for f in (p.rglob("*") if p.is_dir() else [p]) if f.is_file() and f.stat().st_size < 200_000_000]
    texts = []
    for f in sources:
        texts.append((str(f), f.read_text(encoding="utf-8", errors="ignore")))
    if LOG_CONTAINER:
        try:
            p = subprocess.run(["docker", "logs", "--since", "30m", LOG_CONTAINER], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ScanError(f"docker logs failed: {e}") from e
        texts.append((f"docker:{LOG_CONTAINER}", p.stdout + p.stderr))
    hits = []
    for source, text in texts:
        for label, val in values.items():
            n = sum(text.count(v) for v in variants(val))
            if n:
                hits.append((label, source, n))
    return hits, len(texts)


def scanner_selfcheck() -> str:
    """Positive and negative control for scan_database. Returns a note; raises AssertionError if the scanner is blind."""
    planted, other = Canary.random(), Canary.random()
    _psql(f"DROP DATABASE IF EXISTS {SCRATCH_DB};", "postgres")
    _psql(f"CREATE DATABASE {SCRATCH_DB};", "postgres")
    try:
        _psql("CREATE TABLE notes (a text, j jsonb, n bigint);", SCRATCH_DB)
        _psql(f"INSERT INTO notes VALUES ('name: ' || {_sql_str(planted.full_name)}, "
              f"jsonb_build_object('nid', {_sql_str(planted.national_id)}), 5);", SCRATCH_DB)
        found, cols = scan_database(planted.values(), SCRATCH_DB)
        labels = {h[0] for h in found}
        assert {"full_name", "national_id"} <= labels, f"the scanner did not find the planted value; findings: {found}"
        other_hits, _ = scan_database({k: v for k, v in other.values().items() if v not in planted.values().values()},
                                      SCRATCH_DB)
        assert not other_hits, f"the scanner also matched a different random value (false positive): {other_hits}"
        return f"the scanner found the planted value (text and jsonb) and nothing for a different value; {cols} columns checked."
    finally:
        _psql(f"DROP DATABASE IF EXISTS {SCRATCH_DB};", "postgres")
