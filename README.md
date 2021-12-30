# Spatgen: Pattern generator for spaCy

Spatgen is a concise and readable DSL and parser which produces patterns for [spaCy](https://github.com/explosion/spaCy)
which you can use in the [Matcher](https://spacy.io/api/matcher) class.

We think [Matcher](https://spacy.io/api/matcher) is fantastic but writing patterns can become tedious especially if there are several combinations with the same prefix or suffix and if the rules don't fall into any of the `OP` operations provided. This package simplifies the creation of large lists of patterns.

## Example

Here's an example showing how to match some syntax with optional and either-or patterns (you can combine these too):

```python
from spatgen import parser

patterns = r"""
name = example
anchors = [study survey report research datum article review]

++match++
lemma(anchors) aux? adv? verb adp? <det? noun | date> [adp det? <org | gpe>]
"""

parser.parse_str(str(patterns))
```

This will produce a `Sections` object which contains a list of patterns (suitable for `Matcher`) for each heading found in the input. It also has a `get_meta` method which allows you to retrieve extra information about the pattern such as its line number and the raw source that led to its creation.

## Syntax

### Variables

Names can contain lowercase alphabetic characters and underscores only. Values are interpreted as either strings or
arrays of strings and quotation marks are not required.

### Sections

Sections are demarcated by surrounding an identifier with `++` on either side.

### Patterns

Patterns loosely follow command-line syntax format.

* `[a ...]` means whatever inside is optional. A pattern will be generated for combinations with and without this
  option.
* `<a | b | ...>` means either a or b (or more). Patterns are generated for every combination.
* `action(param)` interprets `action` to be one of spaCy's token operators (`LEMMA`, `LOWER`, etc).
    * If `param` is a string surrounded by quotes then the pattern is compared directly (e.g. `{"LEMMA": "say"}`).
    * If `param` is an identifier and is specified as a variable then the pattern is an `IN` pattern (
      e.g. `{"LEMMA": {"IN": var}}`).
* Other terms are interpreted as either POS tags or entity types. These are matched on context so the spaCy pattern will
  have the correct type.
    * E.g. `verb` will produce `{"POS": "VERB"}` but `org` will produce `{"ENT_TYPE": "ORG"}`.
* Every match supports modifiers and will produce the corresponding `OP` entry:
    * `?` will match zero or one
    * `*` will match zero or more
    * `+` will match one or more
    * `!` will ensure that none match

