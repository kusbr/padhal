#!/usr/bin/env python3

from __future__ import annotations

from padhal_app import (
    DATAMUSE_API_URL,
    DICTIONARY_API_URL,
    DatamuseRepository,
    DictionaryRepository,
    GRAY,
    GREEN,
    GuessRecord,
    InMemoryGameStore,
    MAX_GUESSES,
    PadhalGame,
    PadhalService,
    RESET,
    WORD_LENGTH,
    YELLOW,
    colorize_guess,
    filter_candidate_words,
    score_guess,
    validate_guess_format,
)


dictionary_repository = DictionaryRepository()
datamuse_repository = DatamuseRepository()
game_store = InMemoryGameStore()
service = PadhalService(
    dictionary_repository=dictionary_repository,
    datamuse_repository=datamuse_repository,
    game_store=game_store,
)


def request_dictionary_entries(word: str) -> list[dict]:
    return dictionary_repository.request_entries(word)


def request_word_candidates(starts_with: str | None = None, part_of_speech: str | None = None) -> list[dict]:
    return datamuse_repository.request_candidates(
        starts_with=starts_with,
        part_of_speech=part_of_speech,
    )


def is_valid_word(word: str) -> bool:
    return dictionary_repository.is_valid_word(word)


def fetch_definition(word: str) -> str | None:
    return dictionary_repository.fetch_definition(word)


def choose_target_word(
    starts_with: str | None = None,
    part_of_speech: str | None = None,
) -> tuple[str, str]:
    return service._choose_target_word(
        starts_with=starts_with,
        part_of_speech=part_of_speech,
    )


def prompt_guess() -> str:
    while True:
        try:
            guess = input(f"Enter a {WORD_LENGTH}-letter word: ").strip().lower()
        except EOFError:
            print("\nInput ended. Exiting game.")
            raise SystemExit(0)
        error = validate_guess_format(guess)
        if error:
            print(error)
            continue
        return guess


def play_round() -> None:
    try:
        game = service.create_game()
    except RuntimeError as exc:
        print(f"\n{exc}")
        return

    history: list[str] = []
    print("\nPadhal")
    print(f"Guess the {WORD_LENGTH}-letter word in {MAX_GUESSES} tries.")
    print("Answer source: API")
    print("Green = right letter/right spot, yellow = right letter/wrong spot.\n")
    print("Word validation is using dictionaryapi.dev.\n")
    print("Today's hidden answer came from Datamuse and was validated through dictionaryapi.dev.\n")

    while game.status == "in_progress":
        attempt = len(game.guesses) + 1
        print(f"Attempt {attempt}/{MAX_GUESSES}")
        guess = prompt_guess()
        try:
            response = service.submit_guess(game.game_id, guess)
        except ValueError as exc:
            print(f"{exc}\n")
            continue
        line = colorize_guess(guess, response["guesses"][-1]["score"])
        history.append(line)

        print()
        for previous in history:
            print(previous)
        print()

        if response["status"] == "won":
            print(f"You solved it in {attempt} guesses.\n")
            if response["definition"]:
                print(f"Definition: {response['definition']}\n")
            return

    print(f"Out of guesses. The word was {game.target.upper()}.")
    if game.definition:
        print(f"Definition: {game.definition}")
    print()


def main() -> None:
    print("Terminal Padhal")
    while True:
        play_round()
        try:
            again = input("Play again? (y/n): ").strip().lower()
        except EOFError:
            print("\nInput ended. Exiting game.")
            return
        if again not in {"y", "yes"}:
            print("Thanks for playing.")
            return


if __name__ == "__main__":
    main()
