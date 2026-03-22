from __future__ import annotations

from dataclasses import asdict, dataclass, field


WORD_LENGTH = 5
MAX_GUESSES = 6

GREEN = "\033[92m"
YELLOW = "\033[93m"
GRAY = "\033[90m"
RESET = "\033[0m"


def score_guess(guess: str, target: str) -> list[str]:
    result = ["absent"] * WORD_LENGTH
    remaining: dict[str, int] = {}

    for index, (guess_char, target_char) in enumerate(zip(guess, target)):
        if guess_char == target_char:
            result[index] = "correct"
        else:
            remaining[target_char] = remaining.get(target_char, 0) + 1

    for index, guess_char in enumerate(guess):
        if result[index] != "absent":
            continue
        if remaining.get(guess_char, 0) > 0:
            result[index] = "present"
            remaining[guess_char] -= 1

    return result


def colorize_guess(guess: str, score: list[str]) -> str:
    pieces: list[str] = []
    for char, state in zip(guess.upper(), score):
        if state == "correct":
            color = GREEN
        elif state == "present":
            color = YELLOW
        else:
            color = GRAY
        pieces.append(f"{color}{char}{RESET}")
    return " ".join(pieces)


def validate_guess_format(guess: str) -> str | None:
    if len(guess) != WORD_LENGTH:
        return f"Guess must be exactly {WORD_LENGTH} letters."
    if not guess.isalpha():
        return "Guess must contain only letters."
    return None


@dataclass
class GuessRecord:
    guess: str
    score: list[str]

    @classmethod
    def from_dict(cls, data: dict) -> "GuessRecord":
        return cls(
            guess=str(data["guess"]),
            score=list(data["score"]),
        )


@dataclass
class PadhalGame:
    game_id: str
    target: str
    source: str
    guesses: list[GuessRecord] = field(default_factory=list)
    status: str = "in_progress"
    error: str | None = None
    definition: str | None = None

    def submit_guess(self, guess: str) -> GuessRecord:
        normalized_guess = guess.strip().lower()
        error = validate_guess_format(normalized_guess)
        if error:
            raise ValueError(error)
        if self.status != "in_progress":
            raise ValueError("Game is already finished.")

        record = GuessRecord(
            guess=normalized_guess,
            score=score_guess(normalized_guess, self.target),
        )
        self.guesses.append(record)

        if normalized_guess == self.target:
            self.status = "won"
        elif len(self.guesses) >= MAX_GUESSES:
            self.status = "lost"

        return record

    def to_dict(self) -> dict:
        finished = self.status in {"won", "lost"}
        return {
            "game_id": self.game_id,
            "word_length": WORD_LENGTH,
            "max_guesses": MAX_GUESSES,
            "source": self.source,
            "status": self.status,
            "guess_count": len(self.guesses),
            "guesses": [asdict(record) for record in self.guesses],
            "answer": self.target if finished else None,
            "definition": self.definition if finished else None,
            "error": self.error,
        }

    def to_storage_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "target": self.target,
            "source": self.source,
            "guesses": [asdict(record) for record in self.guesses],
            "status": self.status,
            "error": self.error,
            "definition": self.definition,
        }

    @classmethod
    def from_storage_dict(cls, data: dict) -> "PadhalGame":
        return cls(
            game_id=str(data["game_id"]),
            target=str(data["target"]),
            source=str(data["source"]),
            guesses=[GuessRecord.from_dict(item) for item in data.get("guesses", [])],
            status=str(data.get("status", "in_progress")),
            error=data.get("error"),
            definition=data.get("definition"),
        )
