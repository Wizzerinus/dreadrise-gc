from math import ceil
from typing import Dict, List, Optional, Tuple, cast

from shared.card_enums import ManaSymbol
from shared.core_enums import Distribution
from shared.helpers.db_loader import load_cards_from_decks
from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.helpers.magic import process_mana_cost_text
from shared.types.card import Card
from shared.types.deck import Deck

single_costs = [14, 13, 11, 10, 9, 8]
double_costs = [-1, 20, 18, 16, 14, 13]
triple_costs = [-1, -1, 23, 20, 18, 16]
all_costs = [single_costs, double_costs, triple_costs]


def requires_colors(c: Optional[Card], color_combo: ManaSymbol, num: int) -> bool:
    if not c:
        return False

    faces_fixed = c.faces if c.cast_join() else [c.faces[0]]
    colors = cast(List[ManaSymbol], color_combo.split('/'))
    for i in faces_fixed:
        if '/' in color_combo and color_combo in c.mana_cost:
            return c.mana_cost[color_combo] == num

        symbols = [y for x, y in i.mana_cost.items() if x in colors]
        if sum(symbols) == num:
            # we also need to check that every specific color (if 2 colors) has less symbols.
            if len(colors) == 1:
                return True
            bad = False
            for j in colors:
                symbols2 = i.mana_cost.get(j, 0)
                if not symbols2:
                    bad = True
            if not bad:
                return True
    return False


def get_ij_producers(d: Deck, all_cards: Dict[str, Card], color_combo: str, num: int) -> int:
    cc_split = color_combo.split('/')
    cards = [(x, z) for x, z in d.mainboard.items() if all_cards[x].mana_value <= 3 and
             [y for y in cc_split if y in all_cards[x].produces]]
    # this is all cool but we don't want to count e.g. Birds of Paradise for itself or other G cards.
    # but we do want to count it for cards that cost GG, for example
    colors = color_combo.split('/')
    symbol_counts = [sum([y for x, y in all_cards[i].mana_cost.items() if x in colors]) for i, _ in cards]
    cards = [u for u, v in zip(cards, symbol_counts) if v < num]
    creatures = sum([z for x, z in cards if 'Creature' in all_cards[x].types])
    noncreatures = sum([z for x, z in cards if 'Creature' not in all_cards[x].types])
    return ceil(creatures / 2 + noncreatures)


def check_karsten(dist: Distribution, d: Deck) -> List[Tuple[str, str, int, int]]:  # first int- expected, second- found
    """Checks single colored and double colored costs up to 3 symbols. More than 3 symbols are considered 3."""
    all_cards = load_cards_from_decks(dist, [d])
    colors: List[ManaSymbol] = ['white', 'blue', 'black', 'red', 'green', 'colorless', 'snow']
    color_combos: List[ManaSymbol] = ['white/blue', 'blue/black', 'black/red', 'red/green', 'green/white',
                                      'white/black', 'blue/red', 'black/green', 'red/white', 'green/blue']
    answer: List[Tuple[str, str, int, int]] = []
    multiplier = max(1.0, (sum(d.mainboard.values()) / 60) ** 1.2)
    for i in colors + color_combos:
        for j in range(3):
            requirement_cards = [x for x in d.mainboard if requires_colors(all_cards.get(x), i, j + 1)] + \
                                [f'{x} (Sideboard)' for x in d.sideboard if x not in d.mainboard and
                                 requires_colors(all_cards.get(x), i, j + 1)]
            if not requirement_cards:
                continue
            # we need this to be different, in case G card produces G and we have GG, so now we need 16 instead of 20
            prod_number = get_ij_producers(d, all_cards, i, j + 1)
            for k in requirement_cards:
                mana_value = min(all_cards[k.split(' (')[0]].mana_value, 6) - 1
                answer.append((k, i, round(all_costs[j][mana_value] * multiplier), prod_number))
    return answer


def stringify(u: Tuple[str, str, int, int]) -> str:
    color_sym = '{' + u[1].replace('white', 'W').replace('blue', 'U').replace('black', 'B') \
        .replace('red', 'R').replace('green', 'G').replace('snow', 'S').replace('colorless', 'C') + '}'
    return f'<b>{u[0]}</b> - expected {u[2]}x {process_mana_cost_text(color_sym)}, got {u[3]}'


def karsten_dict(dist: Distribution, d: Deck) -> Tuple[DeckCheckStatus, List[str], List[str], List[str]]:
    karsten = check_karsten(dist, d)
    errors = [stringify(x) for x in karsten if x[2] - x[3] >= 3]
    warnings = [stringify(x) for x in karsten if 3 > x[2] - x[3] > 0]
    messages = [stringify(x) for x in karsten if x[2] - x[3] <= 0]
    if errors:
        return deck_check_statuses[2], errors, warnings, messages
    if warnings:
        return deck_check_statuses[1], [], warnings, messages
    return deck_check_statuses[0], [], [], messages
