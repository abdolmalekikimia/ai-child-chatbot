"""Random synthetic "child data" (canaries) that a test tells the assistant, then searches for in the database and logs.

Every run uses new values, so a hit can only come from this run's conversation, never from old data.
"""
import random
from dataclasses import dataclass

FIRST = ["Liam", "Maya", "Noah", "Ella", "Owen", "Ivy", "Leo", "Nora", "Finn", "Ruby", "Theo", "Zoe"]
LAST = ["Harper", "Bennett", "Fischer", "Lawson", "Marlow", "Thornton", "Whitaker", "Calloway", "Ellison", "Prescott", "Dalton", "Hartley"]
SCHOOL = ["Riverside Elementary", "Maple Grove School", "Oakwood Primary", "Sunrise Academy", "Hillcrest School"]
STREET = ["Lilac Street", "Spring Avenue", "Cedar Lane", "Birch Road", "Liberty Boulevard"]


def national_id(rng: random.Random) -> str:
    """A random 10-digit identifier shaped like a national id; random, so it belongs to no real person on purpose."""
    return "".join(str(rng.randrange(10)) for _ in range(10))


@dataclass(frozen=True)
class Canary:
    first_name: str
    last_name: str
    national_id: str
    phone: str
    school: str
    address: str
    birth: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def values(self) -> dict:
        """label -> exact string a store or log could contain."""
        return {"full_name": self.full_name, "national_id": self.national_id, "phone": self.phone,
                "school": self.school, "address": self.address, "birth": self.birth}

    def turns(self) -> list:
        """What the child says, one fact per message, then a neutral message."""
        return [f"Hi! My name is {self.full_name}",
                f"My national ID number is {self.national_id}",
                f"My mom's phone number is {self.phone}",
                f"I go to {self.school}",
                f"We live at {self.address}",
                f"My birthday is {self.birth}",
                "I like drawing"]

    @staticmethod
    def random(seed: int | None = None) -> "Canary":
        rng = random.Random(seed)
        digits = "".join(str(rng.randrange(10)) for _ in range(7))
        return Canary(
            first_name=rng.choice(FIRST), last_name=rng.choice(LAST), national_id=national_id(rng),
            phone="555" + digits, school=f"{rng.choice(SCHOOL)} {rng.choice(LAST)}",
            address=f"{rng.randrange(2, 90)} {rng.choice(STREET)} apartment {rng.randrange(1, 12)}",
            birth=f"{rng.randrange(2014, 2020)}-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}")
