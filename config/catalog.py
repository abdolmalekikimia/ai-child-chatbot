"""Coverage catalog: which scenario groups exist, how they are automated and what each one still depends on."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioGroup:
    key: str             # runner key: SAF, PRV, MEM, ONB
    title: str
    modes: str           # how the scenarios talk to the assistant
    status: str          # Implemented / Partial
    dependency_status: str
    dependency: str
    notes: str


GROUPS = (
    ScenarioGroup("SAF", "Safety, hallucination and content boundaries", "Voice + text", "Implemented", "Partial / needs a reference list",
                  "Approved list of red lines and of allowed knowledge sources",
                  "Word-based verdicts on a small probe set; a real quality evaluation is out of scope"),
    ScenarioGroup("PRV", "Privacy of a synthetic child identity", "Voice + text + data-store scan", "Implemented", "Partial / needs data-store access",
                  "Read-only access to the QA data store and service logs",
                  "A random synthetic identity is told to the assistant, then searched for in storage and logs"),
    ScenarioGroup("MEM", "Cross-session memory of key points", "Voice + text", "Implemented", "Partial / feature may not be wired",
                  "A test environment where the chat path is connected to memory",
                  "Same-session recall and next-session recall are reported separately"),
    ScenarioGroup("ONB", "Voluntary onboarding and non-sensitive memory persistence", "Voice only + data-store reads", "Implemented",
                  "Partial / needs data-store access", "Read-only data store, memory service running",
                  "Before/after reads of the onboarding and memory tables; runs once because the test child is a fixed id"),
)


def find(ref: str) -> ScenarioGroup | None:
    key = ref.upper()
    return next((g for g in GROUPS if g.key == key), None)
