from lark import Lark
from lark.visitors import Transformer
import re
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


class PatternTransformer(Transformer):
    def __init__(self):
        super().__init__(visit_tokens=True)
        self.definitions = {}
        self.sections = {}

    @staticmethod
    def KEYWORD(token):
        return token.upper()

    @staticmethod
    def POS(token):
        return {"POS": str(token)}

    @staticmethod
    def ENT(token):
        return {"ENT_TYPE": str(token)}

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
        if all(isinstance(p, str) for p in patterns):
            self.sections[kind] = patterns
        else:
            flat = list(itertools.chain.from_iterable(patterns))
            self.sections[kind] = flat

    def pattern(self, matches):
        if all(isinstance(m, str) for m in matches):
            return " ".join(matches)
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
                inner = self.pattern(match[0])
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
        return tokens,

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


def parse_str(s: str):
    parser = Lark(GRAMMAR, parser="earley")
    transformer = PatternTransformer()
    tree = parser.parse(s)
    transformer.transform(tree)
    return {
        "definitions": transformer.definitions,
        "sections": transformer.sections
    }


def parse_file(path: str):
    with open(path) as f:
        s = f.read()
    return parse_str(s)
