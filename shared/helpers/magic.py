import logging
import re
from typing import List, Tuple, cast

from jinja2 import Markup

from shared.card_enums import (Color, ManaDict, ManaSymbol, Rarity, color_combo_localization, color_symbols_single,
                               color_symbols_to_colors, color_symbols_to_mana_types, colors, colors_single,
                               mana_symbols, rarities, rarity_map)
from shared.helpers.exceptions import RisingDataError, SearchSyntaxError
from shared.helpers.util import int_def

logger = logging.getLogger('dreadrise.magic')


def process_mana_cost(cost: str) -> List[ManaSymbol]:
    """
    Process mana cost, returning it in the List format.
    :param cost: the mana cost string
    :return: the mana cost list
    """
    reg = re.compile(r'{(.+?)}')
    ans: List[ManaSymbol] = []
    for i in re.findall(reg, cost):
        if '/' in i:
            tup = i.upper().split('/')
            if len(tup) == 2:
                a, b = tup
                force_phyrexian = False
            elif len(tup) == 3:
                a, b, fp = tup
                if fp == 'P':
                    force_phyrexian = True
                else:
                    raise RisingDataError(f'Invalid trisplit mana symbol: {i}.')
            else:
                raise RisingDataError(f'Invalid split level for mana symbol: {i}.')

            if b == 'P' and a in colors_single:
                ans.append(cast(ManaSymbol, 'p' + color_symbols_to_colors[a]))
            elif (a == '2' or a in colors_single) and b in colors_single:
                a = color_symbols_to_colors[a] if a != '2' else a
                b = color_symbols_to_colors[b]
                p = '' if not force_phyrexian else 'p'
                if f'{p}{a}/{b}' in mana_symbols:
                    ans.append(cast(ManaSymbol, f'{p}{a}/{b}'))
                else:
                    ans.append(cast(ManaSymbol, f'{p}{b}/{a}'))
            else:
                raise RisingDataError(f'Invalid split mana symbol: {i}.')
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
                    raise RisingDataError(f'Invalid single-symbol mana symbol: {i}.')
                else:
                    ans.append(color_symbols_to_mana_types[i])
    return ans


def process_mana_cost_dict(cost: str) -> ManaDict:
    """
    Convert cost from the string form to the dictionary form.
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
    if s in rarities:
        return cast(Rarity, s)
    elif s in rarity_map:
        return rarity_map[s]
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
    letters = {
        'P': 'two life',
        'W': 'one white mana',
        'U': 'one blue mana',
        'B': 'one black mana',
        'R': 'one red mana',
        'G': 'one green mana',
        'S': 'one snow mana',
        'T': 'tap this permanent',
        'Q': 'untap this permanent',
        'X': 'any amount of generic mana'
    }

    number_words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                    'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
                    'nineteen', 'twenty']

    def replace(m: re.Match) -> str:
        letter_list = m.groups()
        mana_symbol = '{' + '/'.join(letter_list) + '}'
        mana_string = ''.join(letter_list)
        try:
            description_list = [letters[x] if x in letters else
                                (f'{x} generic mana' if int(x) > 20 else f'{number_words[int(x)]} generic mana')
                                for x in letter_list]
        except ValueError:
            description_list = []
            logger.warning('Broken mana symbol: %s', letter_list)
        description_str = description_list[0] if len(description_list) < 2 else \
            ', '.join(description_list[:-1]) + ' or ' + description_list[-1]
        return f'<abbr class="card-symbol card-symbol-{mana_string}" title="{description_str}">{mana_symbol}</abbr>'

    trisplit = re.compile(r'{(.)/(.)/(.)}')
    o = re.sub(trisplit, replace, o)
    multicolor_regex = re.compile(r'{(.)/(.)}')
    o = re.sub(multicolor_regex, replace, o)
    singlecolor_regex = re.compile(r'{(.)}')
    o = re.sub(singlecolor_regex, replace, o)
    # loyalty_regex = re.compile(r'\[(0|[+-][0-9]+)]') # don't have loyalty symbols
    return Markup(o)
