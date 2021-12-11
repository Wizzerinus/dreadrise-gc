from typing import Dict, Tuple

from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.types.card import Card
from shared.types.deck import Deck


def check_maindeck_size(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    card_count = sum([x for x in d.mainboard.values()])
    if card_count < 60:
        return deck_check_statuses[2], f'Too few cards: expected 60, got {card_count}'
    if card_count > 60:
        return deck_check_statuses[1], f'Too many cards: expected 60, got {card_count}'
    return deck_check_statuses[0], ''


def check_max_count(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    main_side_sum = {}
    for x, y in d.mainboard.items():
        main_side_sum[x] = y
    for x, y in d.sideboard.items():
        main_side_sum[x] = main_side_sum.get(x, 0) + y

    bad_cards = [x for x, y in main_side_sum.items() if x in c and y > c[x].max_count]
    if bad_cards:
        return deck_check_statuses[2], 'The following cards have too many copies of them: ' + ', ' .join(bad_cards)
    return deck_check_statuses[0], ''


def check_sideboard_size(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    card_count = sum([x for x in d.sideboard.values()])
    if card_count < 15:
        return deck_check_statuses[1], f'Too few sideboard cards: expected 15, got {card_count}'
    if card_count > 15:
        return deck_check_statuses[2], f'Too many sideboard cards: expected 15, got {card_count}'
    return deck_check_statuses[0], ''
