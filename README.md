# Disvortilo

Disvortilo is a simple tool that breaks Esperanto words into roots and affixes.

## Getting Started

You can install Disvortilo from PyPI using pip:

```shell
pip install disvortilo
```

## Examples

```python
from disvortilo import Disvortilo, rank

disvortilo = Disvortilo()

print(disvortilo.parse("malliberejo"))
# > [('mal', 'liber', 'ej', 'o')]

# some have more than one possible output
print(disvortilo.parse("esperantistino"))
# > [('esper', 'ant', 'ist', 'in', 'o'), ('esperant', 'ist', 'in', 'o')]

# you can also get the morphemes along their categories
print(disvortilo.parse_detailed("plibonigojn"))
# > [(('pli', WordPart.FULL_WORD), ('bon', WordPart.ROOT), ('ig', WordPart.SUFFIX), ('ojn', WordPart.POS))]

# sort the values from most likely to less likely
print(rank(disvortilo.parse_detailed("envias"), n=2))  # get the 2 most likely options
# > [(('envi', WordPart.ROOT), ('as', WordPart.POS)), (('en', WordPart.FULL_WORD), ('vi', WordPart.FULL_WORD), ('as', WordPart.POS))]
```

## API Reference

### `Disvortilo`

Parser class for splitting Esperanto words into morphemes.

#### `Disvortilo.parse(word: str) -> list[tuple[str, ...]]`

Returns all valid analyses of `word`. Each analysis is a tuple of morpheme strings in order.

Example return value:

```python
[('esper', 'ant', 'ist', 'in', 'o'), ('esperant', 'ist', 'in', 'o')]
```

#### `Disvortilo.parse_detailed(word: str) -> list[tuple[tuple[str, WordPart], ...]]`

Like `parse`, but each morpheme is returned together with its detected category (`WordPart`). Each analysis is a tuple
of `(morpheme, WordPart)` pairs.

Example return value:

```python
[(('pli', WordPart.FULL_WORD), ('bon', WordPart.ROOT), ('ig', WordPart.SUFFIX), ('ojn', WordPart.POS))]
```

### `rank(options, n: int | None = None) -> list[tuple[tuple[str, WordPart], ...]]`

Sorts options based on a heuristic of the most likely option.

Note, that this will only work with the returned values from parse_detailed.

Example return value:
```python
[(('neĝ', WordPart.ROOT), ('is', WordPart.POS)), (('ne', WordPart.FULL_WORD), ('ĝis', WordPart.FULL_WORD))]
```

### `WordPart`

Enum values used by `parse_detailed`:

- `PREFIX`
- `ROOT`
- `SUFFIX`
- `FULL_WORD`
- `POS`
- `NUMBER`
- `NAME`
- `CORRELATIVE_START`
- `CORRELATIVE_END`

### `split_sentence(sentence: str) -> list[str]`

Splits a sentence into Esperanto word-like tokens. Supports Esperanto diacritics, optional trailing apostrophes, and
forms like `3` and `3an`.

Example:

```python
from disvortilo import split_sentence

split_sentence("Mi vidas 3an domon.")
# > ['Mi', 'vidas', '3an', 'domon']
```

### `split_sentence_detailed(sentence: str) -> Generator[tuple[str, int, int], None, None]`

Split a sentence into Esperanto word-line tokens. Unline `split_sentence`, it yields the position of each word.

Example:

```python
from disvortilo import split_sentence_detailed

list(split_sentence_detailed("Mi vidis 3an domon."))
# > [('Mi', 0, 2), ('vidis', 3, 8), ('3an', 9, 12), ('domon', 13, 18)]
```