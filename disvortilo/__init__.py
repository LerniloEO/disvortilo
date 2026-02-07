import enum
import importlib.resources
import re
from collections.abc import Generator
from functools import cache


class WordPart(enum.Enum):
    PREFIX = enum.auto()
    ROOT = enum.auto()
    SUFFIX = enum.auto()
    FULL_WORD = enum.auto()
    # Part of speech
    POS = enum.auto()
    NUMBER = enum.auto()

    CORRELATIVE_START = enum.auto()
    CORRELATIVE_END = enum.auto()

    def __repr__(self):
        return self.name


@cache
def _load_word_list(resource_name: str) -> set[str]:
    result = []
    for line in importlib.resources.files(__package__).joinpath(resource_name).read_text("utf-8").splitlines():
        # Remove comments
        word, _, _ = line.partition("#")
        word = word.strip()

        if word:  # Ignore empty lines
            result.append(word)

    return set(result)


def _growing_string(string: str) -> Generator[str]:
    before = ""
    for char in string:
        before += char
        yield before


WORD_ENDS = {
    "e", "en",
    "a", "an", "ajn", "aj",
    "o", "on", "ojn", "oj",
    "as", "os", "is", "us", "u", "i"
}
CORRELATIVE_WORD_STARTS = {
    "ki", "ti", "i", "ĉi", "neni"
}
CORRELATIVE_WORD_ENDS = {
    "o", "on", "oj", "ojn",
    "u", "un", "uj", "ujn",
    "a",
    "e", "en",
    "am", "el", "es", "om", "al"
}


class Disvortilo:
    def __init__(self):
        self.suffixes = _load_word_list("suffixes.txt")
        self.prefixes = _load_word_list("prefixes.txt")
        self.roots = _load_word_list("roots.txt")
        self.full_words = _load_word_list("full_words.txt")

    def _is_in(self, word: str, _suffix, _prefix, _root, _full_word) -> WordPart | None:
        if _root and word in self.roots:
            return WordPart.ROOT
        elif _suffix and word in self.suffixes:
            return WordPart.SUFFIX
        elif _prefix and word in self.prefixes:
            return WordPart.PREFIX
        elif _full_word and word in self.full_words:
            return WordPart.FULL_WORD

        return None

    def _parse_correlative(self, word: str) -> list[tuple[tuple[str, WordPart], ...]]:
        for part in _growing_string(word):
            if part in CORRELATIVE_WORD_STARTS:
                prefix = part
                remaining = word[len(part):]
                break
        else:
            # word didn't match the word starts
            return []

        if remaining in CORRELATIVE_WORD_ENDS:
            return [((prefix, WordPart.CORRELATIVE_START), (remaining, WordPart.CORRELATIVE_END))]

        return []

    def _parse_number(self, word: str) -> list[tuple[tuple[str, WordPart], ...]]:
        valid = []
        for part in _growing_string(word):
            if part.isdigit():
                remaining = word[len(part):]
                if not remaining:
                    valid.append(((part, WordPart.NUMBER),))
                elif remaining in ("a", "an"):
                    valid.append(((part, WordPart.NUMBER), (remaining, WordPart.POS)))

        return valid

    def parse(self, word: str) -> list[tuple[str, ...]]:
        detailed = self.parse_detailed(word)

        result = []
        for option in detailed:
            result.append(tuple(part[0] for part in option))

        return result

    def parse_detailed(
            self,
            word: str,

            # Controls the valid next part
            _suffix: bool = False,
            _prefix: bool = True,
            _root: bool = True,
            _full_word_integrated: bool = True,
            _correlative: bool = True,
            _full_word_standalone: bool = True,
            _number: bool = True
    ) -> list[tuple[tuple[str, WordPart], ...]]:
        if _full_word_standalone and word in self.full_words:
            return [((word, WordPart.FULL_WORD),)]

        if _correlative:
            correlative = self._parse_correlative(word)
            if correlative:
                return correlative

        if _number:
            number = self._parse_number(word)
            if number:
                return number

        valid = []
        for part in _growing_string(word):
            if check := self._is_in(part, _suffix, _prefix, _root, _full_word_integrated):
                remaining = word[len(part):]
                if remaining.startswith("o") and len(remaining) > 1:
                    remaining_parsed = self.parse_detailed(
                        remaining[1:],
                        _suffix=False,
                        _prefix=False,
                        _correlative=False,
                        _full_word_standalone=False,
                        _number=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append(((part, check), ("o", WordPart.POS)) + parsed_part)

                if check != WordPart.PREFIX and remaining in WORD_ENDS:
                    # Allow if the prefix can be used as a root too. Disallow an end after a prefix
                    valid.append(((part, check), (remaining, WordPart.POS)))
                else:  # try recursion
                    remaining_parsed = self.parse_detailed(
                        remaining,
                        _suffix=True,
                        _correlative=False,
                        _full_word_standalone=False,
                        _number=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append(((part, check),) + parsed_part)

        return valid


_ESPERANTO_SPLIT_WORDS = r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ0-9]+"


def split_sentence(sentence: str):
    return re.findall(_ESPERANTO_SPLIT_WORDS, sentence)
