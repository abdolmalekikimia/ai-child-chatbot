# AI Child Chatbot QA

A QA automation portfolio project for testing a **conversational AI application for children** by driving real conversations
(text over HTTP, voice over a WebSocket) and collecting the evidence needed to judge the assistant's behavior.

> **Read this first.** The product this was built for was **under development (roughly 40% complete)** while the work was done, so many
> capabilities could not be tested reliably. The 40% describes the product, **not** test coverage. This repository is a sanitized, generic
> version of private work: names, endpoints and data were replaced with neutral placeholders and the service contract is a *reference
> contract*. It is not a finished test framework, and automated verdicts are **not** the final decision (see [Testing methodology](#testing-methodology)).

- [Project overview](#project-overview) · [QA testing scope](#qa-testing-scope) · [Testing methodology](#testing-methodology)
- [Current development status](#current-development-status) · [Limitations](#limitations) · [Technology stack](#technology-stack)
- [Project structure](#project-structure) · [Running it](#running-it) · [Security and privacy](#security-and-privacy) · [Portfolio relevance](#portfolio-relevance)
- Deeper technical pages are in the project Wiki (see [Wiki](#wiki)).

## Project overview

**The application (as modeled here):** a voice and text assistant that talks to children. It introduces itself, holds multi-turn conversations,
should refuse unsafe topics, should not invent facts, should not keep identifying data, and is meant to remember a few harmless points
between sessions.

**Why it is hard to test:**
- Replies are free text and vary from run to run, so exact-match assertions do not work.
- The important risks are behavioral: a privacy leak, an unsafe answer, an invented fact, a claim to be human, a wrong "memory".
- Some behavior only appears across sessions (memory) or in storage (what was actually kept), not in the reply itself.
- The voice path adds speech recognition and synthesis on top of the model, and its failures look different from text failures.
- The product was still being built, so "it does not do this yet" has to be told apart from "it does this wrongly".

## QA testing scope

Only what the code in this repository actually does:

| Area | What is implemented | Where |
|---|---|---|
| Conversational behavior | Scripted multi-turn conversations in voice and text; a first conversation and a second in a **new login and session** | `chat/conversations.py` |
| Child privacy / sensitive data | A random **synthetic identity** is told to the assistant; replies, a data store and logs are searched for it; internal-identifier leak probe | `chat/checks_privacy.py`, `chat/canary.py`, `checks/storage_scan.py` |
| Safety scenarios | 12 probes: insult, adult content (also repeated in the same and in a new session), medical advice, claiming to be human | `chat/scenarios_safety.py` |
| Hallucination probes | Facts the assistant cannot know (new product, match result, price, teacher, fake news) plus two known-answer facts | `chat/scenarios_safety.py` |
| Session and memory | Same-session vs next-session recall of an incident, an interest, a preference and a topic; onboarding and memory persistence (voice only) | `chat/scenarios_memory.py`, `chat/scenarios_onboarding.py` |
| Voice interaction | Text-to-speech, 16 kHz PCM16 audio streamed in chunks, reply read from the output transcription | `chat/voice.py`, `chat/stream.py` |
| WebSocket communication | One socket per voice conversation, frames logged as received (audio replaced by its size) | `chat/stream.py` |
| API testing | The text chat is driven through its HTTP calls (session, token, scenario, turns) and every request/response is kept; **there is no separate contract/schema test suite** | `chat/client.py` |
| Database and storage inspection | Read-only search of every text column of every table; before/after row counts; log search; scanner self-check on a scratch database | `checks/storage_scan.py` |
| Test reporting | One HTML report with conversations, evidence, a findings table and explicit outcomes; optional results database | `core/report_html.py`, `core/qa_db.py` |

## Testing methodology

The assistant's behavior is judged from **conversation evidence**, not from an automated label alone.

1. **Automated execution.** The tool logs in, opens the session, tells the scripted lines (as text, or as synthesized speech over the WebSocket)
   and records every exchange, including the exact request and response.
2. **Automated checks.** Simple rules run on the recorded replies and on storage: marker words, regular expressions, searches for the synthetic
   values, before/after table comparisons. They produce a *suggested* outcome.
3. **Human review of the conversational evidence.** The tester reads the actual conversation in the report and compares the assistant's
   replies with the expected behavior: is there a privacy leak, an unsafe answer, an invented fact, an odd pattern?
4. **Final assessment.** The tester decides from the evidence. The automated outcome is an input to that decision, not the decision.

**Why the automated outcome is not final:** the verdicts are word-based. A correct reply worded differently ends as `OBSERVATION`, and a reply
that merely contains a marker word can pass without being good. The report shows `OBSERVATION` precisely when a human must read the transcript.
Manual review is therefore an essential part of this approach today. It is not described here as a replacement for automation.

The outcomes the tool writes are `PASS`, `FAIL`, `BLOCKED` (did not run), `OBSERVATION` (read the transcript) and `NOT BUILT`.
`BLOCKED` is never counted as a pass, and nothing passes by default. Details: Wiki page *Test Execution and Reporting*.

## Current development status

- The product was roughly **40% complete**. The full product was not available for comprehensive end-to-end testing.
- Test coverage is limited by what was ready. **An unavailable or unimplemented feature is not treated as a failed test**; it is reported as
  `NOT BUILT` or `BLOCKED`.
- The current suite is **not complete product validation**.

| Category | Examples |
|---|---|
| Implemented and currently testable | Text and voice conversations, safety and hallucination probes, privacy leak probes in replies |
| Partially implemented, limited testability | Cross-session memory (depends on the chat path being connected to memory); data-store and log scans (depend on read-only access); onboarding (voice only) |
| Cannot yet be tested reliably | User A / user B isolation, sensitive-value screening with screening on, a stable pseudonymous child identifier, barge-in (interrupting a reply), the per-turn evaluation panel |

## Limitations

- **Verdicts are word-based** and not reliable enough to be final. Paraphrase and morphology also mean wording the lists do not know.
- **Manual review is required** for every `OBSERVATION`, and recommended for every reported `PASS`.
- The reference service contract is generic; a real system needs an adapter in `chat/client.py` and `chat/stream.py`.
- Probes, marker words and the speech voice are **English only**.
- The English version in this repository was **not run against a live system**. Earlier runs in a private environment used different (non-English) probes.
- Text-to-speech needs internet and a third-party service; speech recognition quality of the system under test affects voice results.
- `ONB` assumes one fixed test child, so it runs once and needs a clean state to be repeated.
- There are no unit tests for the tool itself; only a built-in self-test against a fake server (it shows the checks run, not that any real system is good).

## Technology stack

From `requirements.txt` and the code:

- **Python 3.12+**, standard library for HTTP (`urllib`, `http.cookiejar`, `ssl`), `asyncio`, `argparse`.
- **websockets** (voice WebSocket client), **edge-tts** (text-to-speech), **miniaudio** (MP3 to PCM16 WAV), **psycopg** (read-only data-store access).
- **PostgreSQL** as the data store that is inspected (through `psycopg`, or `docker exec ... psql` for a local container).
- Optional **SQL Server** for a results database through `sqlcmd` (`database/qa_schema.sql`).
- **PowerShell** wrapper (`run-qa.ps1`); a self-contained **HTML** report; a built-in fake HTTP server for the self-test.

## Project structure

```
run_qa.py / run-qa.ps1      entry point: runs the groups, writes the report, exit codes
chat/
  conversations.py          one conversation flow per scenario group (first and second session, repeats, fail-fast)
  client.py                 HTTP client of the text chat, secret redaction, TLS handling
  stream.py                 WebSocket voice stream
  voice.py                  text-to-speech to PCM16
  scenarios_safety.py       safety and hallucination probes and verdict rules
  scenarios_memory.py       same-session / next-session memory probes
  scenarios_onboarding.py   onboarding and memory persistence (voice only)
  scenarios_privacy.py,
  checks_privacy.py         privacy checks on replies, data store and logs
  canary.py                 random synthetic identity
  selftest_server.py        fake server for the self-test
checks/storage_scan.py      read-only data-store and log scan, scanner self-check
stories/                    one module per scenario group: criteria and "not built" notes
core/                       report generation, results database, data models
config/                     settings, scenario-group catalog, local.env.example (placeholders only)
docs/                       scenario list and a labeled self-test sample report
```

## Running it

Requirements: Python 3.12+, the packages in `requirements.txt`. Copy `config/local.env.example` to `config/local.env` (git-ignored) and fill in your own values.

```powershell
python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt
.\run-qa.ps1 -List                                              # scenario groups and what they depend on
.\run-qa.ps1 -ChatSelftest -ChatMode text -ChatRuns 1           # self-test against the built-in fake server
.\run-qa.ps1 -Task PRV -Base https://test-env.example.invalid   # one group against your own system under test
```

Before any scenario the tool opens the voice session and waits for the assistant to greet. If it does not, the tool prints an error, **writes no
report and saves nothing** (exit code 3). A labeled self-test sample is in `docs/sample/selftest_report.html`; it is **not** a result for any real system.

## Security and privacy

- No keys, tokens, passwords, certificates, real data or company identifiers are committed; `config/local.env`, `config/certs/` and `reports/` are git-ignored.
- **TLS verification is never disabled.** A private CA or pinned certificate can be supplied for this tool only.
- Data-store access is **read-only**. Only **synthetic** identities and sentences are ever sent, including to the text-to-speech service.
- Transcripts that contain the synthetic identity are not stored in the results database. Reports may contain conversation text; review before sharing.

## Portfolio relevance

This project shows practical QA work on a conversational AI application: designing scenarios around real risks (privacy, safety, invented facts,
memory), testing across text, voice, WebSocket and storage, being explicit about what is automated and what needs human judgment, and keeping the
difference between *not built yet* and *broken* visible in the report.

**Authorship note.** The scenario design, the risk analysis and the evaluation approach are the author's work. The code was written with the help of an
AI assistant and should not be read as evidence of independent software-engineering depth.

## Wiki

More detail: Project Overview, Testing Strategy and Methodology, Conversational Testing, Privacy Testing, Safety Testing, API / WebSocket / Voice Testing,
Database and Storage Validation, Test Execution and Reporting, Current Limitations and Development Status.
