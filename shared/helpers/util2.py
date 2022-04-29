import logging
import re
from importlib import import_module
from typing import Callable, Dict, List, Tuple, Union, cast

from shared.card_enums import card_types
from shared.core_enums import Distribution, distributions
from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.dist_constants import DistConstants
from shared.types.set import Expansion

logger = logging.getLogger('dreadrise.util')
reminder_regex = re.compile(r' \((.+?)\)')


def build_deck(deck_list: List[Tuple[int, str, int, bool, int]]) -> Deck:
    """
    Create a deck from the deck builder deck definition.
    :param deck_list: the deck builder definition.
    :return: the resulting Deck object.
    """
    d = Deck()
    d.mainboard = {y: x for x, y, _, z, _ in deck_list if not z}
    d.sideboard = {y: x for x, y, _, z, _ in deck_list if z}
    return d


def get_dist_constants(dist: Distribution) -> DistConstants:
    """
    Get the distribution constants for a specified distribution.
    :param dist: the distribution
    :return: the DistConstants object
    """
    return cast(DistConstants, import_module(f'dists.{dist}.constants'))


def update_distributions() -> None:
    """
    Update all distributions. Called when the web server is starting.
    :return: nothing
    """
    logger.info('Updating the distributions...')
    for i in distributions:
        if i != 'default':
            mod = get_dist_constants(i)
            try:
                mod.Update()
                logger.info(f'Updated {i}')
            except AttributeError:
                logger.info(f'Update function for {i} does not exist')


def get_card_sorter(cards: Dict[str, Card]) -> Callable[[str], Tuple[int, str]]:
    """
    Create the function sorting cards.
    :param cards: the card dictionary the cards should be drawn from
    :return: the resulting function, can be used as the key parameter
    """

    def card_sorter(name: str) -> Tuple[int, str]:
        if name not in cards:
            return -1, name

        card = cards[name]
        try:
            type_index = card_types.index(card)
        except ValueError:
            type_index = 9

        return card.mana_value + type_index * 30, name

    return card_sorter


def calculate_color_data(deck: Deck, cards: Dict[str, Card]) -> List[float]:
    """
    Calculate the color data for a deck.
    :param deck: the deck in question
    :param cards: the card dictionary including all the cards in the deck
    :return: list of 5 numbers - % of WUBRG symbols (from 0.0-1.0)
    """

    color_index = {'white': 0, 'blue': 1, 'black': 2, 'red': 3, 'green': 4}
    counts = [0, 0, 0, 0, 0]
    for i, c in deck.mainboard.items():
        if i not in cards:
            continue
        for j, k in cards[i].mana_cost.items():
            if j in color_index:
                counts[color_index[j]] += k * c

    count_sum = sum(counts)
    if not count_sum:
        return [x / 1.0 for x in counts]
    return [x / count_sum for x in counts]


def print_card(card: Union[dict, Card]) -> str:
    true_card = Card().load(card) if isinstance(card, dict) else card
    card_face = true_card.faces[0]
    name, cost, oracle = card_face.name, card_face.mana_cost_str, card_face.oracle
    ctype, cpow, ctou, cloy = card_face.types, card_face.power, card_face.toughness, card_face.loyalty
    oracle = reminder_regex.sub('', oracle)
    if 'Creature' in ctype:
        power_text = f'{cpow}/{ctou}'
    elif 'Planeswalker' in ctype:
        power_text = f'{cloy} SL'
    else:
        power_text = ''
    return f'{name} {cost} {power_text}\n{ctype}\n{oracle}'


def compare_cards(card1: Union[dict, Card], card2: Union[dict, Card], expansions: Dict[str, Expansion] = None) -> str:
    """
    Compares two cards on having identical text. If expansion dict is passed, assumes the first card can be different
    from the second one if its first print is earlier. Otherwise, assumes the cards must be identical.
    :param card1: the "template" card
    :param card2: the "newly found" card
    :param expansions: used to determine dates
    :return: the comparison result
    """
    ct1, ct2 = print_card(card1), print_card(card2)
    if ct1 == ct2:
        return ''

    warning = True
    if expansions:
        sets1, sets2 = card1.get('sets', []), card2.get('sets', [])
        e1, e2 = [expansions[x].release_date for x in sets1], [expansions[x].release_date for x in sets2]
        warning = not e1 or not e2 or min(e1) > min(e2)

    warning_str = 'Warning!' if warning else 'Notice!'
    return f'{warning_str}\nCard 1: {ct1}\nCard 2: {ct2}\n'
