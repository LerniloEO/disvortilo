# Disvortilo

Disvortilo is a simple tool that breaks Esperanto words into roots and affixes.

## Getting Started

You can install Disvortilo from PyPI using pip:

```shell
pip install disvortilo
```

## Examples

```python
from disvortilo import Disvortilo

disvortilo = Disvortilo()

print(disvortilo.parse("malliberejo"))
# > [('mal', 'liber', 'ej', 'o')]

# some have more than one possible output
# like "Esperanto" which means "a hoping person"
print(disvortilo.parse("esperantistino"))
# > [('esper', 'ant', 'ist', 'in', 'o'), ('esperant', 'ist', 'in', 'o')]
```
