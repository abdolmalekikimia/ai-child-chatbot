"""Shared helper for the scenario groups: take the rows and conversations that chat/conversations.py produced for one group."""


def chat_rows(options, key: str, conversations: list) -> list:
    central = getattr(options, "central", None)  # run once for all groups by run_qa.py; None without a base URL or --chat-selftest
    if central is None:
        return []
    conversations += central.conversations[key]
    return central.rows[key]
