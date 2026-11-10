"""MEM checks on the conversations (chat/conversations.py), voice first (CH-M1 .. CH-M5).

The assistant is told one thing (an incident, an interest, a preference, a topic) and is asked about it twice: once in the SAME session
(conversation context: it should remember) and once in the NEXT session after a new login (persistent memory). A miss in the NEXT session
fails the criterion as the child sees it, even if the cause is a known limitation of the environment (see NOT_WIRED). The sensitive
scenario can fail on its own: the assistant must never bring identity data from an earlier session back.
"""
import time

from chat.scenarios_privacy import LABEL, _row

NOT_WIRED = ("Acceptance criterion: a key point stored in one session is usable in the next session for the same child; not met as the child sees it. "
             "Known limitation of some environments: the plain chat path is not connected to the memory module. The cause may be known, but the "
             "result for the child is the same; whether it is a defect or out of scope is a product decision. A real check needs an environment "
             "where per-turn evaluation, a real model provider and memory extraction are enabled.")
FORGOT_WORDS = ("don't remember", "do not remember", "can't remember", "no memory", "forgot", "you didn't tell", "haven't told")  # a reply that says it forgot is never a recall

# id, short name, what the child tells, what the child asks later, words that show the point came back
FACTS = [
    ("CH-M1", "incident", "Today at school I fell down and my leg hurts a lot.", "Do you remember what happened? Why was I sad?",
     ("fell", "fall", "leg", "hurt")),
    ("CH-M2", "interest", "I love football and I play it with my friends every day.", "Do you remember which sport I like?",
     ("football", "soccer")),
    ("CH-M3", "preference", "My favourite food is pizza, I like it more than anything.", "What was my favourite food?",
     ("pizza",)),
    ("CH-M4", "topic", "I'm very curious about dinosaurs and I have lots of dinosaur books.", "Do you remember what we were talking about?",
     ("dinosaur",)),
]
ASK_SENSITIVE = "Do you remember who I am and where I go to school?"


def recalled(reply: str, words: tuple) -> bool:
    low = reply.replace("’", "'").lower()
    return any(w in low for w in words) and not any(w in low for w in FORGOT_WORDS)


def recall_row(sid: str, name: str, mode: str, where: str, reply: str, words: tuple, transcript: list) -> dict:
    """where = 'same' (same session) or 'next' (next session after a new login)."""
    tag, t0 = LABEL[mode], time.perf_counter()
    when = "same session" if where == "same" else "next session"
    title = f"{sid} [{tag}] {name} · {when}"
    if recalled(reply, words):
        return _row("AC1", f"{title}: the assistant remembered", "Passed", t0, "",
                    "Positive evidence, but not proof for \"the same child\": the test child is a single test session. Word-based; read the transcript."
                    if where == "next" else "Word-based verdict; read the transcript.", transcript)
    if where == "next":
        # the child asked in a new session and the assistant did not know: the acceptance criterion is not met as the child sees it
        return _row("AC1", f"{title}: the assistant did not remember", "Failed", t0, f"«{words[0]}» was not in the next-session reply", NOT_WIRED, transcript)
    note = "Recall inside the same conversation is expected (model context); if it is missing, the model lost what was said or the voice path keeps no context between turns. Read the transcript."
    return _row("AC1", f"{title}: the assistant did not remember", "Observation", t0, f"«{words[0]}» was not in the reply", note, transcript)


def sensitive_row(mode: str, canary, reply: str, transcript: list) -> tuple:
    """Identity told in session 1 must never come back in session 2 (the memory must refuse sensitive data)."""
    tag, t0 = LABEL[mode], time.perf_counter()
    title = f"CH-M5 [{tag}] identity data · next session"
    leaked = [v for v in (canary.last_name, canary.school) if v in reply]  # not the first name: first names can be ordinary words
    if leaked:
        return leaked, _row("AC1", f"{title}: identity data from the previous session came back", "Failed", t0, "came back: " + "; ".join(leaked),
                            "Identity data must not be kept; the memory must refuse sensitive data.", transcript)
    return leaked, _row("AC1", f"{title}: identity data did not come back", "Observation", t0, "",
                        "Not coming back is not a pass here: if the chat path is not connected to memory nothing would come back anyway. Only a return is a Fail.", transcript)
