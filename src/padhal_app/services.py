from __future__ import annotations

import json
import os
import random
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import RLock
from urllib.error import HTTPError, URLError

from .domain import PadhalGame
from .repositories import DatamuseRepository, DictionaryRepository

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency in local test runs
    redis = None


class InMemoryGameStore:
    def __init__(self) -> None:
        self.games: dict[str, PadhalGame] = {}
        self._target_last_used_at: dict[str, datetime] = {}
        self._game_locks: dict[str, RLock] = {}
        self._lock = RLock()

    def save(self, game: PadhalGame) -> PadhalGame:
        with self._lock:
            self.games[game.game_id] = game
            self._target_last_used_at[game.target] = datetime.now(timezone.utc)
            self._game_locks.setdefault(game.game_id, RLock())
        return game

    def get_recently_used_targets(self, block_window: timedelta, now: datetime) -> set[str]:
        cutoff = now - block_window
        with self._lock:
            return {
                target
                for target, last_used_at in self._target_last_used_at.items()
                if last_used_at >= cutoff
            }

    def reset_target_usage_window(self) -> None:
        with self._lock:
            self._target_last_used_at.clear()

    def get(self, game_id: str) -> PadhalGame:
        with self._lock:
            game = self.games.get(game_id)
        if game is None:
            raise KeyError(f"Unknown game id: {game_id}")
        return game

    def get_lock(self, game_id: str) -> RLock:
        with self._lock:
            lock = self._game_locks.get(game_id)
        if lock is None:
            raise KeyError(f"Unknown game id: {game_id}")
        return lock

    @contextmanager
    def lock_game(self, game_id: str):
        lock = self.get_lock(game_id)
        with lock:
            yield


class RedisGameStore:
    def __init__(self, redis_url: str, key_prefix: str = "padhal") -> None:
        if redis is None:
            raise RuntimeError("redis package is required for Redis-backed game storage.")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix

    def _game_key(self, game_id: str) -> str:
        return f"{self.key_prefix}:game:{game_id}"

    def _lock_key(self, game_id: str) -> str:
        return f"{self.key_prefix}:lock:{game_id}"

    def _used_targets_key(self) -> str:
        return f"{self.key_prefix}:used_targets_by_time"

    def save(self, game: PadhalGame) -> PadhalGame:
        now_ts = datetime.now(timezone.utc).timestamp()
        self.client.set(self._game_key(game.game_id), json.dumps(game.to_storage_dict()))
        self.client.zadd(self._used_targets_key(), {game.target: now_ts})
        return game

    def get_recently_used_targets(self, block_window: timedelta, now: datetime) -> set[str]:
        cutoff_ts = (now - block_window).timestamp()
        used_targets = self.client.zrangebyscore(self._used_targets_key(), cutoff_ts, "+inf")
        return {str(target) for target in used_targets}

    def reset_target_usage_window(self) -> None:
        self.client.delete(self._used_targets_key())

    def get(self, game_id: str) -> PadhalGame:
        payload = self.client.get(self._game_key(game_id))
        if payload is None:
            raise KeyError(f"Unknown game id: {game_id}")
        return PadhalGame.from_storage_dict(json.loads(payload))

    @contextmanager
    def lock_game(self, game_id: str):
        lock = self.client.lock(self._lock_key(game_id), timeout=10, blocking_timeout=5)
        acquired = lock.acquire()
        if not acquired:
            raise RuntimeError("Could not acquire lock for game.")
        try:
            yield
        finally:
            try:
                lock.release()
            except Exception:
                pass


def build_game_store() -> InMemoryGameStore | RedisGameStore:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return RedisGameStore(redis_url)
    return InMemoryGameStore()


class PadhalService:
    TARGET_REUSE_BLOCK_WINDOW = timedelta(days=30)

    def __init__(
        self,
        dictionary_repository: DictionaryRepository | None = None,
        datamuse_repository: DatamuseRepository | None = None,
        game_store: InMemoryGameStore | RedisGameStore | None = None,
    ) -> None:
        self.dictionary_repository = dictionary_repository or DictionaryRepository()
        self.datamuse_repository = datamuse_repository or DatamuseRepository()
        self.game_store = game_store or build_game_store()

    def create_game(
        self,
        starts_with: str | None = None,
        part_of_speech: str | None = None,
    ) -> PadhalGame:
        target, source = self._choose_target_word(
            starts_with=starts_with,
            part_of_speech=part_of_speech,
        )
        return self.game_store.save(
            PadhalGame(
                game_id=str(uuid.uuid4()),
                target=target,
                source=source,
            )
        )

    def get_game(self, game_id: str) -> PadhalGame:
        return self.game_store.get(game_id)

    def submit_guess(self, game_id: str, guess: str) -> dict:
        normalized_guess = guess.strip().lower()
        with self.game_store.lock_game(game_id):
            game = self.get_game(game_id)

            if any(record.guess == normalized_guess for record in game.guesses):
                raise ValueError("You already guessed that word.")

            if not self.dictionary_repository.is_valid_word(normalized_guess):
                raise ValueError("Guess is not a valid English word.")

            game.submit_guess(normalized_guess)

            if game.status in {"won", "lost"} and game.definition is None:
                game.definition = self.dictionary_repository.fetch_definition(game.target)

            self.game_store.save(game)
            return game.to_dict()

    def _choose_target_word(
        self,
        starts_with: str | None = None,
        part_of_speech: str | None = None,
    ) -> tuple[str, str]:
        now = self._utc_now()
        used_targets = self.game_store.get_recently_used_targets(
            self.TARGET_REUSE_BLOCK_WINDOW,
            now,
        )

        try:
            candidates = self.datamuse_repository.list_candidate_words(
                starts_with=starts_with,
                part_of_speech=part_of_speech,
            )
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(f"Unable to fetch answer candidates from the API: {exc}") from exc

        random.shuffle(candidates)
        if not candidates:
            raise RuntimeError("The API returned no usable 5-letter candidates.")

        available_candidates = [candidate for candidate in candidates if candidate not in used_targets]
        if not available_candidates:
            self.game_store.reset_target_usage_window()
            available_candidates = candidates

        for candidate in available_candidates:
            try:
                if self.dictionary_repository.request_entries(candidate):
                    self.dictionary_repository.word_validity_cache[candidate] = True
                    return candidate, "api"
            except HTTPError as exc:
                if exc.code == 404:
                    continue
                raise RuntimeError(f"Unable to validate API candidate '{candidate}': {exc}") from exc
            except (URLError, TimeoutError, ValueError) as exc:
                raise RuntimeError(f"Unable to validate API candidate '{candidate}': {exc}") from exc

        raise RuntimeError("The API candidates were fetched, but none validated as dictionary words.")

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)
