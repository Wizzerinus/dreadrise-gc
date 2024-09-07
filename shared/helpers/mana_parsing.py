import pyparsing as pp

from shared.card_enums import color_symbols_to_colors, colors, colors_single, mana_symbols, \
    misc_to_mana_symbols, misc_symbols
from shared.helpers.exceptions import RisingDataError


def mana_cost_filter() -> pp.OneOrMore:
    left_brace = pp.Literal('{').suppress()
    right_brace = pp.Literal('}').suppress()
    word = pp.Word(pp.alphanums, pp.alphanums + '/')
    word.set_parse_action(lambda t: t[0].replace('/', ''))
    num = pp.Word(pp.nums)
    num.set_parse_action(lambda t: int(t[0]))
    sym = pp.Char('WUBRGSCVX') | num
    symbol = (left_brace + word + right_brace) | sym
    return pp.OneOrMore(symbol)


def get_mana_cost(query: str) -> list[int | str]:
    syntax = mana_cost_filter()

    ans: list[int | str] = []
    for i in syntax.parse_string(query.upper()):
        if isinstance(i, int):
            ans.append(i)
        else:
            if len(i) > 2 and i in colors:
                ans.append(i)
            elif len(i) == 1 and i in colors_single:
                ans.append(color_symbols_to_colors[i])
            elif i in misc_symbols:
                ans.append(misc_to_mana_symbols[i])
            elif len(i) == 2 and i[0] in colors and i[1] in colors:
                c1 = color_symbols_to_colors[i[0]]
                c2 = color_symbols_to_colors[i[1]]
                if f'{c1}/{c2}' in mana_symbols:
                    ans.append(f'{c1}/{c2}')
                elif f'{c2}/{c1}' in mana_symbols:
                    ans.append(f'{c2}/{c1}')
            else:
                raise RisingDataError(f'Unknown mana symbol: {i}')

    return ans
