import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import padhal
from padhal_app.repositories import DatamuseRepository, DictionaryRepository
from padhal_app.services import InMemoryGameStore, PadhalService


class DictionaryRepositoryTests(unittest.TestCase):
    def test_is_valid_word_accepts_dictionary_response(self) -> None:
        repository = DictionaryRepository()

        with patch.object(repository, "request_entries", return_value=[{"word": "crane"}]):
            self.assertTrue(repository.is_valid_word("crane"))

    def test_is_valid_word_rejects_404_response(self) -> None:
        repository = DictionaryRepository()
        error = HTTPError(padhal.DICTIONARY_API_URL, 404, "Not Found", None, None)

        with patch.object(repository, "request_entries", side_effect=error):
            self.assertFalse(repository.is_valid_word("qzxjk"))

        self.assertTrue(repository.online_enabled)

    def test_is_valid_word_accepts_any_five_letter_word_on_network_error(self) -> None:
        repository = DictionaryRepository()

        with patch.object(repository, "request_entries", side_effect=URLError("offline")):
            self.assertTrue(repository.is_valid_word("crane"))
            self.assertTrue(repository.is_valid_word("qzxjk"))

        self.assertFalse(repository.online_enabled)

    def test_fetch_definition_returns_first_available_definition(self) -> None:
        repository = DictionaryRepository()
        entries = [
            {
                "meanings": [
                    {
                        "definitions": [
                            {"definition": "a large wading bird with a long neck"}
                        ]
                    }
                ]
            }
        ]

        with patch.object(repository, "request_entries", return_value=entries):
            self.assertEqual(
                repository.fetch_definition("crane"),
                "a large wading bird with a long neck",
            )


class DatamuseRepositoryTests(unittest.TestCase):
    def test_filter_candidate_words_keeps_only_five_letter_alpha_words(self) -> None:
        candidates = [
            {"word": "crane"},
            {"word": "sea"},
            {"word": "abc12"},
            {"word": "stone"},
        ]

        self.assertEqual(
            padhal.filter_candidate_words(candidates),
            ["crane", "stone"],
        )

    def test_filter_candidate_words_can_filter_by_prefix_and_part_of_speech(self) -> None:
        candidates = [
            {"word": "crane", "tags": ["n"]},
            {"word": "crash", "tags": ["v"]},
            {"word": "crown", "tags": ["n"]},
        ]

        self.assertEqual(
            padhal.filter_candidate_words(candidates, starts_with="cr", part_of_speech="n"),
            ["crane", "crown"],
        )

    def test_list_candidate_words_uses_repository_filtering(self) -> None:
        repository = DatamuseRepository()
        candidates = [{"word": "crane"}, {"word": "abc12"}]

        with patch.object(repository, "request_candidates", return_value=candidates):
            self.assertEqual(repository.list_candidate_words(), ["crane"])


class ServiceTests(unittest.TestCase):
    def test_create_game_uses_repositories_and_store(self) -> None:
        dictionary_repository = DictionaryRepository()
        datamuse_repository = DatamuseRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, datamuse_repository, game_store)

        with patch.object(datamuse_repository, "list_candidate_words", return_value=["crane"]), patch.object(
            dictionary_repository,
            "request_entries",
            return_value=[{"word": "crane"}],
        ), patch("padhal_app.services.random.shuffle", side_effect=lambda items: None):
            game = service.create_game(starts_with="c", part_of_speech="n")

        self.assertEqual(game.target, "crane")
        self.assertIs(game_store.get(game.game_id), game)

    def test_create_game_raises_when_candidate_source_fails(self) -> None:
        service = PadhalService(DictionaryRepository(), DatamuseRepository(), InMemoryGameStore())

        with patch.object(service.datamuse_repository, "list_candidate_words", side_effect=URLError("offline")):
            with self.assertRaises(RuntimeError):
                service.create_game()

    def test_submit_guess_records_progress(self) -> None:
        dictionary_repository = DictionaryRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, DatamuseRepository(), game_store)
        game = game_store.save(padhal.PadhalGame(game_id="game-1", target="crane", source="api"))

        response = service.submit_guess(game.game_id, "slate")

        self.assertEqual(response["status"], "in_progress")
        self.assertEqual(response["guess_count"], 1)
        self.assertEqual(response["guesses"][0]["guess"], "slate")

    def test_submit_guess_fetches_definition_on_win(self) -> None:
        dictionary_repository = DictionaryRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, DatamuseRepository(), game_store)
        game = game_store.save(padhal.PadhalGame(game_id="game-1", target="crane", source="api"))

        with patch.object(dictionary_repository, "fetch_definition", return_value="a tall bird"):
            response = service.submit_guess(game.game_id, "crane")

        self.assertEqual(response["status"], "won")
        self.assertEqual(response["answer"], "crane")
        self.assertEqual(response["definition"], "a tall bird")

    def test_submit_guess_rejects_invalid_english_word(self) -> None:
        dictionary_repository = DictionaryRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, DatamuseRepository(), game_store)
        game = game_store.save(padhal.PadhalGame(game_id="game-1", target="crane", source="api"))

        with patch.object(dictionary_repository, "is_valid_word", return_value=False):
            with self.assertRaises(ValueError):
                service.submit_guess(game.game_id, "qzxjk")

        self.assertEqual(game.status, "in_progress")
        self.assertEqual(len(game.guesses), 0)

    def test_submit_guess_rejects_duplicate_guess(self) -> None:
        dictionary_repository = DictionaryRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, DatamuseRepository(), game_store)
        game = game_store.save(padhal.PadhalGame(game_id="game-1", target="crane", source="api"))

        with patch.object(dictionary_repository, "is_valid_word", return_value=True):
            service.submit_guess(game.game_id, "slate")
            with self.assertRaises(ValueError):
                service.submit_guess(game.game_id, "slate")

        self.assertEqual(len(game.guesses), 1)

    def test_submit_guess_is_safe_under_concurrent_requests(self) -> None:
        dictionary_repository = DictionaryRepository()
        game_store = InMemoryGameStore()
        service = PadhalService(dictionary_repository, DatamuseRepository(), game_store)
        game = game_store.save(padhal.PadhalGame(game_id="game-1", target="crane", source="api"))

        with patch.object(dictionary_repository, "is_valid_word", return_value=True), patch.object(
            dictionary_repository,
            "fetch_definition",
            return_value=None,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(service.submit_guess, game.game_id, "slate"),
                    executor.submit(service.submit_guess, game.game_id, "pride"),
                ]
                results = [future.result() for future in futures]

        self.assertEqual(len(game.guesses), 2)
        self.assertEqual({record.guess for record in game.guesses}, {"slate", "pride"})
        self.assertTrue(all(result["guess_count"] in {1, 2} for result in results))


class DomainTests(unittest.TestCase):
    def test_score_guess_marks_all_correct_letters(self) -> None:
        self.assertEqual(
            padhal.score_guess("crane", "crane"),
            ["correct", "correct", "correct", "correct", "correct"],
        )

    def test_score_guess_handles_duplicate_letters(self) -> None:
        self.assertEqual(
            padhal.score_guess("allee", "apple"),
            ["correct", "present", "absent", "absent", "correct"],
        )

    def test_score_guess_limits_present_matches_to_available_letters(self) -> None:
        self.assertEqual(
            padhal.score_guess("eerie", "pearl"),
            ["absent", "correct", "present", "absent", "absent"],
        )

    def test_colorize_guess_wraps_letters_in_expected_colors(self) -> None:
        rendered = padhal.colorize_guess(
            "crane",
            ["correct", "present", "absent", "correct", "absent"],
        )
        expected = " ".join(
            [
                f"{padhal.GREEN}C{padhal.RESET}",
                f"{padhal.YELLOW}R{padhal.RESET}",
                f"{padhal.GRAY}A{padhal.RESET}",
                f"{padhal.GREEN}N{padhal.RESET}",
                f"{padhal.GRAY}E{padhal.RESET}",
            ]
        )
        self.assertEqual(rendered, expected)

    def test_prompt_guess_retries_until_valid_input(self) -> None:
        with patch("builtins.input", side_effect=["no", "ab12!", "CrAnE"]), patch(
            "builtins.print"
        ) as mock_print:
            result = padhal.prompt_guess()

        self.assertEqual(result, "crane")
        mock_print.assert_any_call("Guess must be exactly 5 letters.")
        mock_print.assert_any_call("Guess must contain only letters.")


if __name__ == "__main__":
    unittest.main()
