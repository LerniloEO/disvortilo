import importlib.resources
import re
from collections.abc import Generator


def load_word_list(resource_name: str) -> set[str]:
    result = []
    for line in importlib.resources.files(__package__).joinpath(resource_name).read_text("utf-8").splitlines():
        # Remove comments
        word, _, _ = line.partition("#")
        word = word.strip()

        if word:  # Ignore empty lines
            result.append(word)

    return set(result)


def growing_string(string: str) -> Generator[str]:
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
        self.suffixes = load_word_list("suffixes.txt")
        self.prefixes = load_word_list("prefixes.txt")
        self.roots = load_word_list("roots.txt")
        self.full_words = load_word_list("full_words.txt")

    def _is_in(self, word: str, _suffix, _prefix, _root, _full_word):
        if _root and word in self.roots:
            return "root"
        elif _suffix and word in self.suffixes:
            return "suffix"
        elif _prefix and word in self.prefixes:
            return "prefix"
        elif _full_word and word in self.full_words:
            return "full_words"

        return ""

    def _parse_correlative(self, word: str) -> list[tuple[str, ...]]:
        for part in growing_string(word):
            if part in CORRELATIVE_WORD_STARTS:
                prefix = part
                remaining = word[len(part):]
                break
        else:
            # word didn't match the word starts
            return []

        if remaining in CORRELATIVE_WORD_ENDS:
            return [(prefix, remaining)]

        return []

    def _parse_number(self, word: str) -> list[tuple[str, ...]]:
        valid = []
        for part in growing_string(word):
            if part.isdigit():
                remaining = word[len(part):]
                if not remaining:
                    valid.append((part,))
                elif remaining in ("a", "an"):
                    valid.append((part, remaining))

        return valid

    def parse(
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
    ) -> list[tuple[str, ...]]:
        if _full_word_standalone and word in self.full_words:
            return [(word,)]

        if _correlative:
            correlative = self._parse_correlative(word)
            if correlative:
                return correlative

        if _number:
            number = self._parse_number(word)
            if number:
                return number

        valid = []
        for part in growing_string(word):
            if check := self._is_in(part, _suffix, _prefix, _root, _full_word_integrated):
                remaining = word[len(part):]
                if remaining.startswith("o") and len(remaining) > 1:
                    remaining_parsed = self.parse(
                        remaining[1:],
                        _correlative=False,
                        _full_word_standalone=False,
                        _suffix=False,
                        _prefix=False,
                        _number=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append((part, "o") + parsed_part)

                if check != "prefix" and remaining in WORD_ENDS:
                    # Allow if the prefix can be used as a root too. Disallow an end after a prefix
                    valid.append((part, remaining))
                else:  # try recursion
                    remaining_parsed = self.parse(
                        remaining,
                        _correlative=False,
                        _full_word_standalone=False,
                        _suffix=True,
                        _number=False
                    )
                    for parsed_part in remaining_parsed:
                        valid.append((part,) + parsed_part)

        return valid


_ESPERANTO_SPLIT_WORDS = r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ0-9]+"


def _split_sentence(sentence: str):
    return re.findall(_ESPERANTO_SPLIT_WORDS, sentence)


def _parse_sentence(sentence: str):
    words = _split_sentence(sentence)

    disvortilo = Disvortilo()

    parsed_words = (disvortilo.parse(word) or word for word in words)

    end = "\n"
    sep = "·"

    for parsed in parsed_words:
        if isinstance(parsed, str):
            print(f"~{parsed}~", end=end)
        else:
            print("    ".join(sep.join(option) for option in parsed), end=end)

    print()
