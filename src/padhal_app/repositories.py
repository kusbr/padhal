from __future__ import annotations

import json
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .domain import WORD_LENGTH


DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
DATAMUSE_API_URL = "https://api.datamuse.com/words"
REQUEST_TIMEOUT_SECONDS = 3
DATAMUSE_MAX_RESULTS = 200
HTTP_HEADERS = {
    "User-Agent": "padhal-cli/1.0",
    "Accept": "application/json",
}


def filter_candidate_words(
    candidates: list[dict],
    starts_with: str | None = None,
    part_of_speech: str | None = None,
) -> list[str]:
    normalized_prefix = (starts_with or "").lower()
    filtered: list[str] = []

    for item in candidates:
        if not isinstance(item, dict):
            continue
        word = item.get("word", "").lower()
        if len(word) != WORD_LENGTH or not word.isalpha():
            continue
        if normalized_prefix and not word.startswith(normalized_prefix):
            continue
        if part_of_speech:
            tags = item.get("tags", [])
            if part_of_speech not in tags:
                continue
        filtered.append(word)

    return filtered


class DictionaryRepository:
    def __init__(self) -> None:
        self.word_validity_cache: dict[str, bool] = {}
        self.online_enabled = True
        self._lock = RLock()

    def request_entries(self, word: str) -> list[dict]:
        request = Request(f"{DICTIONARY_API_URL}{word}", headers=HTTP_HEADERS)
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)

    def is_valid_word(self, word: str) -> bool:
        if len(word) != WORD_LENGTH or not word.isalpha():
            return False

        normalized = word.lower()
        with self._lock:
            if normalized in self.word_validity_cache:
                return self.word_validity_cache[normalized]
            online_enabled = self.online_enabled

        is_valid = False
        if online_enabled:
            try:
                is_valid = bool(self.request_entries(normalized))
            except HTTPError as exc:
                if exc.code != 404:
                    with self._lock:
                        self.online_enabled = False
            except (URLError, TimeoutError, json.JSONDecodeError):
                with self._lock:
                    self.online_enabled = False

        with self._lock:
            if not is_valid and not self.online_enabled:
                is_valid = True
            self.word_validity_cache[normalized] = is_valid

        return is_valid

    def fetch_definition(self, word: str) -> str | None:
        with self._lock:
            if not self.online_enabled:
                return None

        try:
            entries = self.request_entries(word.lower())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None

        for entry in entries:
            for meaning in entry.get("meanings", []):
                for definition in meaning.get("definitions", []):
                    text = definition.get("definition")
                    if text:
                        return text
        return None


class DatamuseRepository:
    def request_candidates(
        self,
        starts_with: str | None = None,
        part_of_speech: str | None = None,
    ) -> list[dict]:
        pattern = "?" * WORD_LENGTH
        if starts_with:
            prefix = starts_with.lower()[:WORD_LENGTH]
            pattern = f"{prefix}{'?' * (WORD_LENGTH - len(prefix))}"

        params = {"sp": pattern, "max": DATAMUSE_MAX_RESULTS}
        metadata_parts = ["p"]
        if part_of_speech:
            metadata_parts.append("f")
        params["md"] = "".join(metadata_parts)
        query = urlencode(params)
        request = Request(f"{DATAMUSE_API_URL}?{query}", headers=HTTP_HEADERS)
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)

    def list_candidate_words(
        self,
        starts_with: str | None = None,
        part_of_speech: str | None = None,
    ) -> list[str]:
        candidates = self.request_candidates(
            starts_with=starts_with,
            part_of_speech=part_of_speech,
        )
        return filter_candidate_words(
            candidates,
            starts_with=starts_with,
            part_of_speech=part_of_speech,
        )
