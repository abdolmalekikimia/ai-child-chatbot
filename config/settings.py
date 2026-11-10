"""Paths and environment. Everything environment-specific comes from environment variables or the git-ignored config/local.env."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_local_env() -> None:
    """Read config/local.env (git-ignored) into os.environ without overriding values already set."""
    f = PROJECT_ROOT / "config" / "local.env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


_load_local_env()
REPORTS_DIR = PROJECT_ROOT / "reports"
RAW_DIR = REPORTS_DIR / "raw"

# ---- HTTP / WebSocket API of the system under test (a reference contract; point these at your own service) -------------------------------
BASE_URL = os.environ.get("CHATQA_BASE_URL", "")
ROUTE_SESSION = os.environ.get("CHATQA_ROUTE_SESSION", "/api/auth/session")        # POST {"key": ...} -> sets a session cookie
ROUTE_TOKEN = os.environ.get("CHATQA_ROUTE_TOKEN", "/api/auth/token")              # POST -> {"token": ...}
ROUTE_SCENARIOS = os.environ.get("CHATQA_ROUTE_SCENARIOS", "/api/scenarios")       # POST -> 201 {"scenario_id", "opening"}; POST <id>/turns
ROUTE_STREAM = os.environ.get("CHATQA_ROUTE_STREAM", "/api/realtime/stream")       # WebSocket for the voice conversation

# ---- TLS: verification is always on; a private CA / pinned certificate can be supplied for this tool only -----------------------------------
CA_FILE = Path(os.environ["CHATQA_CA_FILE"]) if os.environ.get("CHATQA_CA_FILE") else None
DB_CA_FILE = Path(os.environ["CHATQA_DB_CA_FILE"]) if os.environ.get("CHATQA_DB_CA_FILE") else None

# ---- Read-only access to the QA data store used by the privacy and memory checks --------------------------------------------------------
DB_CONTAINER = os.environ.get("CHATQA_DB_CONTAINER", "qa-postgres")      # local container, when the data store runs in Docker
DB_NAME = os.environ.get("CHATQA_DB_NAME", "qa_data_store")
LOG_PATHS = [p for p in os.environ.get("CHATQA_LOG_PATHS", "").split(os.pathsep) if p]   # log files or folders to search
LOG_CONTAINER = os.environ.get("CHATQA_LOG_CONTAINER", "")                                  # service container name, if any
DB_REMOTE = {k: os.environ.get(f"CHATQA_DB_{k.upper()}", "") for k in ("host", "port", "user", "password")}
DB_REMOTE["sslmode"] = os.environ.get("CHATQA_DB_SSLMODE", "verify-full")
DB_REMOTE_ON = bool(DB_REMOTE["host"])

# Queries for the onboarding / memory checks (read-only SELECTs; adapt the table names to your data store).
INTRO_SQL = os.environ.get("CHATQA_INTRO_SQL", "select kind, value from memory_store.intro_items order by 1, 2")
MEMORY_SQL = os.environ.get("CHATQA_MEMORY_SQL", "select note from memory_store.memory_notes order by 1")

# Voice clips of a run are kept in reports/audio/<report name>/, named like the report. Set by run_qa.py.
AUDIO_ROOT = REPORTS_DIR / "audio"
AUDIO_DIR: Path | None = None
