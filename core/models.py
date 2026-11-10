"""Plain data shared by every story."""
from dataclasses import dataclass, field


@dataclass
class Story:
    """Everything one scenario group contributes to the combined report."""
    key: str                      # "331"
    title: str                    # "ID"
    subtitle: str                 # one-line description
    criteria: list                # [(ac_id, description, [backend test classes that give evidence])]
    rows: list = field(default_factory=list)     # dicts: cls, name, outcome, dur, msg, note, details
    checks: list = field(default_factory=list)   # (title, status, note): static checks on the source
    conversations: list = field(default_factory=list)  # dicts: title, mode, setup, turns[(who, text, clip)], searched[(where, what, result)]
