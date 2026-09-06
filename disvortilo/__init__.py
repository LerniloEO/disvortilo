import enum
import importlib.resources
import re
from collections.abc import Generator
from functools import cache


class WordPart(enum.Enum):
    """Semantic categories assigned to parsed Esperanto morphemes.

    The values are used by :meth:`Disvortilo.parse_detailed` to label each
    segment of a parsed word.
    """

    PREFIX = enum.auto()
    ROOT = enum.auto()
    SUFFIX = enum.auto()
    FULL_WORD = enum.auto()
    # Part of speech
    POS = enum.auto()
    NUMBER = enum.auto()
    NAME = enum.auto()

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
    "as", "os", "is", "us", "u", "i",
    "'"
}
CORRELATIVE_WORD_STARTS = {
    "ki", "ti", "i", "ĉi", "neni"
}
CORRELATIVE_WORD_ENDS = {
    "o", "on", "oj", "ojn",
    "u", "un", "uj", "ujn",
    "a", "an", "aj", "ajn",
    "e", "en",
    "am", "el", "es", "om", "al"
}
INTERFIXES = {
    "o", "i", "a", "e"
}
PERSONAL_PRONOUNS = {
    "mi", "vi", "ŝi", "li", "ĝi", "oni", "ri", "ni", "ili", "si"
}


class Disvortilo:
    """Parser for splitting Esperanto words into morphemes.

    The parser combines built-in lexicons for roots, affixes, full words,
    personal names, and country names to produce one or more valid analyses.
    """

    def __init__(self):
        """Initialize parser dictionaries from packaged resource files."""

        self.suffixes = _load_word_list("suffixes.txt")
        self.prefixes = _load_word_list("prefixes.txt")
        self.roots = _load_word_list("roots.txt")
        self.full_words = _load_word_list("full_words.txt")
        self.names = _load_word_list("names.txt")
        self.countries = _load_word_list("countries.txt")

        self.roots.update(self.countries)  # all country names are also roots.

    def _is_in(self, word: str, _suffix, _prefix, _root, _full_word) -> WordPart | None:
        if _suffix and word in self.suffixes:
            return WordPart.SUFFIX
        elif _prefix and word in self.prefixes:
            return WordPart.PREFIX
        elif _full_word and word in self.full_words:
            return WordPart.FULL_WORD
        elif _root and word in self.roots:
            return WordPart.ROOT

        return None

    def _parse_correlative(self, word: str, _allow_remaining: bool = False) -> list[tuple[tuple[str, WordPart], ...]]:
        for part in _growing_string(word):
            if part in CORRELATIVE_WORD_STARTS:
                prefix = part
                remaining = word[len(part):]
                break
        else:
            # word didn't match the word starts
            return []

        valid = []
        for end in _growing_string(remaining):
            if end in CORRELATIVE_WORD_ENDS:
                after_correlative = remaining[len(end):]
                if not after_correlative:
                    # Complete correlative, no remaining text
                    valid.append(((prefix, WordPart.CORRELATIVE_START), (end, WordPart.CORRELATIVE_END)))
                elif _allow_remaining:
                    # Correlative with remaining text - will be handled by caller
                    valid.append(((prefix, WordPart.CORRELATIVE_START), (end, WordPart.CORRELATIVE_END)))

        return valid

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

    def _parse_name(self, word: str):
        valid = []
        for part in _growing_string(word):
            remaining = word[len(part):]
            if remaining[:2] in {"ĉj", "nj"} and remaining[2:] in WORD_ENDS:
                valid.append(((part, WordPart.NAME), (remaining[:2], WordPart.SUFFIX), (remaining[2:], WordPart.POS)))

            elif part in self.names:
                if remaining in WORD_ENDS:
                    valid.append(((part, WordPart.NAME), (remaining, WordPart.POS)))
                elif not remaining:
                    valid.append(((part, WordPart.NAME),))

        return valid

    def parse(self, word: str) -> list[tuple[str, ...]]:
        """Return all valid morpheme segmentations for a word.

        Args:
            word: Esperanto word to analyze.

        Returns:
            A list of valid analyses. Each analysis is a tuple of morpheme
            strings in order.
        """

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
            _number: bool = True,
            _name: bool = True
    ) -> list[tuple[tuple[str, WordPart], ...]]:
        """Return all valid analyses with category labels for each segment.

        Args:
            word: Esperanto word to analyze.
            _suffix: Internal recursion flag for enabling suffix matching.
            _prefix: Internal recursion flag for enabling prefix matching.
            _root: Internal recursion flag for enabling root matching.
            _full_word_integrated: Internal recursion flag for enabling
                full-word matching as part of larger words.
            _correlative: Internal recursion flag for enabling correlative
                parsing.
            _full_word_standalone: Internal recursion flag for enabling
                whole-word full-word matches.
            _number: Internal recursion flag for enabling number parsing.
            _name: Internal recursion flag for enabling personal-name parsing.

        Returns:
            A list of valid analyses. Each analysis is a tuple of
            ``(segment, WordPart)`` pairs in order.
        """

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

        if _name:
            name = self._parse_name(word)
            if name:
                return name

        valid = []

        if _correlative:
            correlative_matches = self._parse_correlative(word, _allow_remaining=True)
            for correlative_parts in correlative_matches:
                # calculate the length of the correlative
                correlative_length = sum(len(part[0]) for part in correlative_parts)
                remaining = word[correlative_length:]

                if not remaining:
                    valid.append(correlative_parts)
                elif remaining in WORD_ENDS:
                    valid.append(correlative_parts + ((remaining, WordPart.POS),))
                else:
                    remaining_parsed = self.parse_detailed(
                        remaining,
                        _suffix=True,
                        _prefix=False,
                        _root=True,
                        _correlative=False,
                        _full_word_standalone=False,
                        _number=False,
                        _name=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append(correlative_parts + parsed_part)

        for part in _growing_string(word):
            if check := self._is_in(part, _suffix, _prefix, _root, _full_word_integrated):
                remaining = word[len(part):]
                if len(remaining) > 1 and remaining[0] in INTERFIXES:
                    remaining_parsed = self.parse_detailed(
                        remaining[1:],
                        _suffix=False,
                        _prefix=False,
                        _correlative=False,
                        _full_word_standalone=False,
                        _number=False,
                        _name=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append(((part, check), (remaining[0], WordPart.POS)) + parsed_part)

                if (check != WordPart.PREFIX
                        and (remaining in WORD_ENDS or ((part in self.countries and remaining == "io")
                                                        or (part in PERSONAL_PRONOUNS and remaining == "n")))
                ):
                    # Allow if the prefix can be used as a root too. Disallow an end after a prefix
                    valid.append(((part, check), (remaining, WordPart.POS)))
                else:  # try recursion
                    remaining_parsed = self.parse_detailed(
                        remaining,
                        _suffix=check != WordPart.PREFIX,  # Disallow words without roots like praanto
                        _correlative=False,
                        # Allow words like malantaŭ and dudek
                        _full_word_standalone=check in {WordPart.PREFIX, WordPart.FULL_WORD},
                        _number=False,
                        _name=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append(((part, check),) + parsed_part)

        return valid


def rank(options: list[tuple[tuple[str, WordPart], ...]], n: int | None = None) -> list[
    tuple[tuple[str, WordPart], ...]]:
    """
    Sorts options based on a heuristic of the most likely option.

    Note, that this will only work with the returned values from parse_detailed.
    """

    def key(option):
        option = tuple(x[0] for x in option)
        lengths = list(map(len, option))
        max_length = max(lengths)
        return (
            len(option),  # Prefer fewer parts
            min(lengths) - max_length,  # Prefer bigger length difference between parts
            lengths.index(max_length)  # Prefer earlier longest parts
        )

    if len(options) == 0 or len(options) == 1:
        return options

    if n == 1:
        return [min(options, key=key)]

    return sorted(options, key=key)[:n]


_ESPERANTO_SPLIT_WORDS = r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ][A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ0-9]*'?|[0-9]+(?:an?)?"


def split_sentence(sentence: str) -> list[str]:
    """Split a sentence into Esperanto word-like tokens.

    The tokenizer keeps Esperanto diacritics, optional trailing apostrophes,
    and numeric forms such as ``3`` and ``3an``.

    Args:
        sentence: Raw sentence text.

    Returns:
        A list of token strings.
    """

    return re.findall(_ESPERANTO_SPLIT_WORDS, sentence)


def split_sentence_detailed(sentence: str) -> Generator[tuple[str, int, int], None, None]:
    """
    Split a sentence into Esperanto word-line tokens. Unline `split_sentence`, it yields the position of each word.

    Args:
        sentence: Raw sentence text.

    Yields:
        The token string, the start, and the end
    """
    for match in re.finditer(_ESPERANTO_SPLIT_WORDS, sentence):
        yield sentence[match.start():match.end()], match.start(), match.end()
