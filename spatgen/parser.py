from lark import Lark
from lark.visitors import Transformer, v_args
from dataclasses import dataclass
from typing import List, TypeVar, Union, Any
import re
import json
import itertools

GRAMMAR = r"""
start: var+ section+

var: IDENT "=" (WORD|ARRAY) _NL+
section: "++" IDENT "++" _NL pattern+
pattern: (WORD+ | match)+ _NL
match: (action | POS | ENT | optional | selection) MODIFIER?
action: KEYWORD "(" (WORD | STRING)? ")"
optional: "[" match+ "]"
selection: "<" match+ (separator match+)+ ">"
!separator: "|"

KEYWORD: "lemma"|"lower"|"orth"|"norm"|"shape"|"prefix"|"suffix"|"is_alpha"|"is_ascii"|"is_digit"|"is_lower"|"is_punct"|"is_space"|"is_title"|"is_upper"|"like_url"|"like_num"|"like_email"|"is_stop"|"is_bracket"|"is_quote"|"is_left_punct"|"is_right_punct"|"is_currency"
POS.1: "adj"|"adp"|"adv"|"aux"|"conj"|"cconj"|"det"|"intj"|"noun"|"num"|"part"|"pron"|"propn"|"punct"|"sconj"|"sym"|"verb"|"x"|"eol"|"space"
ENT.1: "person"|"norp"|"facility"|"org"|"gpe"|"loc"|"product"|"event"|"work_of_art"|"language"|"date"|"time"|"percent"|"money"|"quantity"|"ordinal"|"cardinal"
MODIFIER: "?"|"*"|"+"|"!"
ARRAY: "[" [WORD (" "+ WORD)*] "]"
IDENT: ("a".."z"|"_")+
WORD: ("a".."z"|"-"|"_")+
STRING: "\"" WORD "\""

%import common.ESCAPED_STRING
%import common.NEWLINE -> _NL
%import common.WS_INLINE

%ignore WS_INLINE
"""


@dataclass
class Pattern:
    section: str
    raw: str
    expanded: Union[List[dict], str]
    line: int

    def __hash__(self):
        return hash(json.dumps(self.expanded, sort_keys=True))


class PatternTransformer(Transformer):
    def __init__(self, s: str):
        super().__init__(visit_tokens=True)
        self._lines = s.splitlines()
        self.definitions = {}
        self.patterns = []

    @staticmethod
    def KEYWORD(token):
        return token.upper()

    @staticmethod
    def POS(token):
        return {"POS": str(token).upper()}

    @staticmethod
    def ENT(token):
        return {"ENT_TYPE": str(token).upper()}

    @staticmethod
    def MODIFIER(token):
        return {"OP": str(token)}

    @staticmethod
    def ARRAY(s):
        return s[1:-1].split()

    @staticmethod
    def IDENT(ident):
        return str(ident)

    @staticmethod
    def WORD(word):
        return str(word)

    @staticmethod
    def STRING(token):
        return str(token)

    def var(self, tokens):
        key, val = tokens[0], tokens[1]
        self.definitions[key] = val

    def section(self, children):
        kind, patterns = str(children[0]), children[1:]
        for line, pattern_list in patterns:
            raw = self._lines[line - 1]
            if isinstance(pattern_list, str):
                pattern = Pattern(kind, raw, pattern_list, line)
                self.patterns.append(pattern)
            elif isinstance(pattern_list, list):
                for pattern in pattern_list:
                    pattern = Pattern(kind, raw, pattern, line)
                    self.patterns.append(pattern)

    def _expand_matches(self, matches):
        patterns = []
        for match in matches:
            if isinstance(match, dict) and len(patterns) == 0:
                patterns.append([match])
            elif isinstance(match, dict):
                for pat in patterns:
                    pat.append(match)
            elif isinstance(match, list) and len(patterns) == 0:
                patterns = match
            elif isinstance(match, list):
                new_patterns = []
                for option in match:
                    with_option = [p + option for p in patterns]
                    new_patterns += with_option
                patterns = new_patterns
            elif isinstance(match, tuple) and len(patterns) == 0:
                patterns.append([])
                patterns += match[0]
            elif isinstance(match, tuple):
                inner = self._expand_matches(match[0])
                if len(inner) == 1:
                    with_option = [p + inner[0] for p in patterns]
                    patterns += with_option
                elif len(inner) > 1:
                    new_patterns = []
                    for option in inner:
                        with_option = [p + option for p in patterns]
                        new_patterns += with_option
                    patterns += new_patterns
        return patterns

    @v_args(tree=True)
    def pattern(self, tree):
        matches = tree.children
        line = tree.meta.line
        if all(isinstance(m, str) for m in matches):
            return line, " ".join(matches)
        return line, self._expand_matches(matches)

    @staticmethod
    def match(children):
        if len(children) == 1:
            return children[0]
        elif len(children) == 2 and "OP" in children[-1]:
            return {**children[0], **children[1]}
        else:
            return children

    def action(self, tokens):
        if len(tokens) == 1:
            return {tokens[0]: True}

        kw, s = tokens[0], tokens[1]
        match = re.search(r"^\"(.+)\"$", s)
        if match:
            return {tokens[0]: match.groups()[0]}
        else:
            return {tokens[0]: {"IN": self.definitions[s]}}

    @staticmethod
    def optional(tokens):
        return (tokens,)

    @staticmethod
    def selection(children):
        options = [[]]
        for child in children:
            if child:
                options[-1].append(child)
            else:
                options.append([])
        return options

    @staticmethod
    def separator(_):
        return None


T = TypeVar("T")


class Sections:
    definitions: dict

    def __init__(self, patterns: List[Pattern], definitions: dict):
        it = itertools.groupby(patterns, key=lambda p: p.section)
        self.definitions = definitions
        self._sections = {}
        for section, group in it:
            self._sections[section] = [p.expanded for p in group]
        self._meta = {hash(p): p for p in patterns}

    def get_meta(self, pattern: List[dict]) -> Pattern:
        key = hash(json.dumps(pattern, sort_keys=True))
        return self._meta[key]

    def keys(self) -> List[str]:
        return list(self._sections.keys())

    def get(self, section: str, default: T) -> Union[List[List[dict]], T]:
        if section in self._sections:
            return self._sections[section]
        else:
            return default

    def __getitem__(self, section: str) -> List[List[dict]]:
        return self._sections[section]


def parse_str(s: str) -> Sections:
    parser = Lark(GRAMMAR, parser="earley", propagate_positions=True)
    transformer = PatternTransformer(s)
    tree = parser.parse(s)
    transformer.transform(tree)
    return Sections(transformer.patterns, transformer.definitions)


def parse_file(path: str) -> Sections:
    with open(path) as f:
        s = f.read()
    return parse_str(s)
