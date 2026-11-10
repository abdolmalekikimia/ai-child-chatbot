"""MEM: minimal persistent memory (key points kept between sessions, not the whole history).

Voice and text conversations: an incident, an interest, a preference and a topic are told, then asked in the SAME session and again in a NEW
session after a new login. Same-session recall is an observation if missed; next-session recall is a failure if missed, even when the cause is
a known limitation (the chat path not being wired to the memory module). Identity data told in session 1 must never come back.
"""
from core.models import Story
from stories._common import chat_rows

KEY = "MEM"

CRITERIA = [
    ("AC1", "A key point stored in one session is usable in the next session for the same child", []),
]


def run(options) -> Story:
    story = Story(KEY, "MEM", "Cross-session memory of key points", CRITERIA)
    story.rows += chat_rows(options, KEY, story.conversations)
    story.checks = [
        ("Live two-session test for one child with turn evaluation", "not_checked",
         "Needs an environment where the chat path is connected to memory, per-turn evaluation is on and a real model provider is configured."),
        ("Definition of a key point, extraction rules and retention period", "not_checked",
         "The requirement is still open; numbers in the reference implementation are not an approved product decision."),
        ("Promotion, sensitive-data filter, expiry and deletion tests", "not_checked",
         "Backend unit/integration suites; not part of this black-box repository."),
    ]
    return story
