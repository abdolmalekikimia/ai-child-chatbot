"""ONB: voluntary onboarding and real non-sensitive memory persistence (voice only).

Only the voice conversation plus read-only before/after reads of the onboarding and memory tables of the QA data store (the reference
system's text chat is not wired to them). The test child is a fixed id, so the group runs once. See chat/scenarios_onboarding.py.
"""
from core.models import Story
from stories._common import chat_rows

KEY = "ONB"

CRITERIA = [
    ("AC1", "The assistant introduces itself and asks voluntarily; not answering does not block the conversation", []),
    ("AC2", "An incomplete onboarding continues in later sessions; missing data is never invented", []),
    ("AC3", "A real non-sensitive point is recalled in a separate later session; an untold memory is never claimed", []),
    ("AC4", "A point of user A does not enter the replies for user B", []),
    ("AC5", "Identity, contact, location, financial data and PINs do not enter the memory", []),
]


def run(options) -> Story:
    story = Story(KEY, "ONB", "Voluntary onboarding and non-sensitive memory", CRITERIA)
    story.rows += chat_rows(options, KEY, story.conversations)
    story.checks = [
        ("Isolation between user A and user B", "not_checked",
         "Not testable through the client (the test child is one fixed id per environment); needs a backend integration test."),
        ("Sensitive-value screening with the screening switch on", "not_checked",
         "In a demo configuration the screening may be off; the conclusive check is a backend test with it on. The conversation only shows "
         "what was stored in this configuration."),
        ("Interrupting the assistant mid-reply (barge-in)", "not_checked", "The tool does not speak over the assistant's reply; manual for now."),
        ("Per-turn evaluation panel", "not_checked", "Visible only in the web playground; not observable from this tool."),
    ]
    return story
