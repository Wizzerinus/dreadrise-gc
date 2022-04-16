from itertools import chain
from typing import Dict, Tuple

from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.types.card import Card
from shared.types.deck import Deck


def check_fusion_legality(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if d.format != 'fusion':
        return deck_check_statuses[0], ''

    cards = list(set(chain(d.mainboard.keys(), d.sideboard.keys())))

    msem_cards = {x for x in cards if x in c and c[x].legality['msem'] == 'legal'}
    modern_cards = [x for x in cards if x in c and c[x].legality['modern'] == 'legal' and x not in msem_cards]
    if len(modern_cards) > 1:
        return deck_check_statuses[2], 'Too many cards from Modern: ' + ', ' .join(modern_cards)
    return deck_check_statuses[0], ''
