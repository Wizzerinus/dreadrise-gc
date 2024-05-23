from typing import Any

import pyparsing as pp

pp.ParserElement.enable_left_recursion()

default_separators: list[str] = ['=', ':', '>', '<', '>=', '<=']


class SearchToken:
    name: str = 'default'
    comparator: str = ':'
    value: Any = ''
    invert: bool = False
    magic: str = ''

    def __init__(self, data: str | list[str]):
        if isinstance(data, str):
            data = [data]
        if len(data) >= 1:
            self.value = data[-1]
            if len(data) >= 2:
                self.comparator = data[-2]
                if len(data) >= 3:
                    if '.' in data[-3]:
                        self.name, self.magic = data[-3].split('.')[0:2]
                    else:
                        self.name = data[-3]
                    if len(data) >= 4:
                        self.invert = data[-4] == '-'

        if self.value == 'or' or self.value == 'and' or self.value == 'nor' or self.value == 'nand':
            self.name = '_operator'

    def __repr__(self) -> str:
        return f'SearchToken<{self.name} {self.comparator} {self.value}>'


class SearchGroup:
    negated: bool = False
    items: list
    modifiers: str

    def __init__(self, things: list):
        if isinstance(things[0], str):
            self.modifiers = things.pop(0)
        else:
            self.modifiers = ''

        if '-' in self.modifiers:
            self.negated = True
        self.items = things

    def __repr__(self) -> str:
        negate = 'Negated' if self.negated else ''
        items = str(self.items)
        return f'{negate}SearchGroup{items}'


class _SearchToken(pp.Or):
    def __init__(self, separators: list[str] | None = None):
        if separators is None:
            separators = default_separators
        alphanums = pp.alphanums + '-_@/~,.\'#'
        letters = alphanums + ' *:{}()\\/'
        operator = pp.one_of(' '.join(separators))
        quote = pp.Literal('"').suppress()
        finish = quote + pp.Word(letters) + quote | pp.Word(alphanums)
        ex = pp.Group(pp.Literal('-') * (0, 1) + pp.Word(alphanums) + operator + finish)
        super().__init__([ex, pp.Word(alphanums)])
        self.set_parse_action(lambda t: SearchToken(t[0]))


class _SearchGroup(pp.Group):
    def __init__(self, expr: pp.ParserElement):
        super().__init__(expr)
        self.set_parse_action(lambda t: SearchGroup(t[0]))


def get_search_splitter() -> pp.Forward:
    thing = pp.Forward()
    left = pp.Literal('(').suppress()
    right = pp.Literal(')').suppress()
    modifiers = pp.Optional(pp.Word('@~-?!'))
    # word = pp.Word(pp.alphanums + '!@-:><=')
    word = _SearchToken()
    atom = pp.Group(word + pp.QuotedString('"')) | pp.QuotedString('"') | word
    atom_or_braced_block = pp.Forward()
    atom_or_braced_block <<= _SearchGroup(modifiers + left + thing + right) | atom
    thing <<= thing + atom_or_braced_block | atom_or_braced_block
    return thing


def tokenize_string(data: str) -> pp.ParseResults:
    return get_search_splitter().parse_string(data)
