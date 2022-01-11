import re
from typing import List, Tuple, cast

from jinja2 import Markup

from shared.card_enums import (Color, ManaDict, ManaSymbol, Rarity, color_combo_localization, color_symbols_single,
                               color_symbols_to_colors, color_symbols_to_mana_types, colors, colors_single,
                               mana_symbols, rarities)
from shared.helpers.exceptions import RisingDataError, SearchSyntaxError
from shared.helpers.util import int_def


def process_mana_cost(cost: str) -> List[ManaSymbol]:
    """
    Processes mana cost, returning it in the List format.
    :param cost: the mana cost string
    :return: the mana cost list
    """
    reg = re.compile(r'{(.+?)}')
    ans: List[ManaSymbol] = []
    for i in re.findall(reg, cost):
        if '/' in i:
            a, b = i.upper().split('/')
            if b == 'P' and a in colors_single:
                ans.append(cast(ManaSymbol, 'p' + color_symbols_to_colors[a]))
            elif (a == '2' or a in colors_single) and b in colors_single:
                if f'{a}/{b}' in mana_symbols:
                    ans.append(cast(ManaSymbol, f'{a}/{b}'))
                else:
                    ans.append(cast(ManaSymbol, f'{b}/{a}'))
            else:
                raise RisingDataError(f'Unknown mana symbol: {i}.')
        else:
            g = int_def(i, -1)
            if g > -1:
                if g > 20 or g < 0:
                    raise RisingDataError(f'Invalid number mana symbol: {g}.')
                elif g == 0:
                    ans.append('zero')
                else:
                    for k in range(g):
                        ans.append('any')
            else:
                i = i.upper()
                if i == 'X':
                    ans.append('x')
                elif i not in color_symbols_single:
                    raise RisingDataError(f'Unknown mana symbol: {i}.')
                else:
                    ans.append(color_symbols_to_mana_types[i])
    return ans


def process_mana_cost_dict(cost: str) -> ManaDict:
    """
    Converts cost in string form to dictionary.
    :param cost: the mana cost in string form
    :return: the resulting mana cost
    """
    arr = process_mana_cost(cost)
    ans: ManaDict = {}
    for i in arr:
        ans[i] = ans.get(i, 0) + 1
    return ans


def calculate_mana_value(cost: ManaDict) -> int:
    """
    Calculates mana value based on the card's cost.
    :param cost: The card's mana cost in dictionary form
    :return: mana value of the card
    """
    return sum([2 * c if x[0] == 'p' else (0 if x == 'zero' or x == 'x' else c) for x, c in cost.items()])


def get_rarity(s: str) -> Rarity:
    """
    Returns the Rarity enum element based on the rarity string.
    :param s: the rarity received.
    :return: the respective Rarity enum element
    """
    s = s.lower()
    if s == 'mythic rare':
        return 'mythic'
    elif s == 'basic land':
        return 'basic'
    elif s in rarities:
        return cast(Rarity, s)
    elif s == 'bonus' or s == 's':
        return 'special'
    raise RisingDataError(f'Unknown rarity: {s}')


def get_color_combination(s: str) -> Tuple[Color, ...]:
    if s in colors:
        return cast(Color, s),
    if s in color_combo_localization:
        return color_combo_localization[s]
    things = [color_symbols_to_colors[x] for x in s.upper() if x in colors_single]
    if len(things) == len(s):
        return tuple(things)
    raise SearchSyntaxError(f'Unknown color: {s}')


def process_oracle(o: str) -> str:
    # o = o.replace('\n\n\n\n', '<br /><hr /><br />')
    o = o.rstrip()
    newline_regex = re.compile(r'\n+')
    o = re.sub(newline_regex, '<br />', o)
    reminder_regex = re.compile(r'\((.+?)\)')
    o = re.sub(reminder_regex, r'<i>(\1)</i>', o)
    o = process_mana_cost_text(o)
    return Markup(o)


def process_mana_cost_text(o: str) -> str:
    multicolor_regex = re.compile(r'{(.)/(.)}')
    o = re.sub(multicolor_regex, r'<abbr class="card-symbol card-symbol-\1\2">{\1/\2}</abbr>', o)
    singlecolor_regex = re.compile(r'{([^}]+)}')
    o = re.sub(singlecolor_regex, r'<abbr class="card-symbol card-symbol-\1">{\1}</abbr>', o)
    # loyalty_regex = re.compile(r'\[(0|[+-][0-9]+)]') # don't have loyalty symbols
    return Markup(o)
