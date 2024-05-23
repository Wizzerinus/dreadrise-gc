import logging
from itertools import chain

from shared.card_enums import Color
from shared.types.card import Card
from shared.types.deck import Deck

logger = logging.getLogger('dreadrise.tagging.color')


def color_rule_applies(d: Deck, cards: dict[str, Card], colors: set[Color]) -> bool:
    """
    Check whether a color rule applies to a deck.
    :param d: the deck to test
    :param cards: the card dictionary
    :param colors: the set of colors to test
    :return: true if the rule applies, false otherwise
    """
    used_colors = set()
    i: str
    for i in chain(d.mainboard.keys(), d.sideboard.keys()):
        if i not in cards:
            logger.warning(f'Card {i} not found')
            continue
        for c in cards[i].cast_colors:
            used_colors.add(c)
    return colors == used_colors
