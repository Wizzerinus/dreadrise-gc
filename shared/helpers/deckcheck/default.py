from itertools import chain
from typing import Dict, Tuple

from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.types.card import Card
from shared.types.deck import Deck


def check_maindeck_size(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    count = sum([x for x in d.mainboard.values()])
    expected_size = 100 if 'EDH' in d.format.upper() or 'COMMANDER' in d.format.upper() else 60
    force_upper = expected_size == 100
    if count < expected_size:
        return deck_check_statuses[2], f'Too few cards: expected {expected_size}, got {count}'
    if count > expected_size:
        return deck_check_statuses[2 if force_upper else 1], f'Too many cards: expected {expected_size}, got {count}'
    return deck_check_statuses[0], ''


def check_max_count(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    main_side_sum = {}
    for x, y in d.mainboard.items():
        main_side_sum[x] = y
    for x, y in d.sideboard.items():
        main_side_sum[x] = main_side_sum.get(x, 0) + y

    if 'EDH' in d.format.upper() or 'COMMANDER' in d.format.upper():  # ew
        bad_cards = [x for x, y in main_side_sum.items() if x not in c or (y > 1 and not (y <= c[x].max_count > 4))]
    else:
        bad_cards = [x for x, y in main_side_sum.items() if x not in c or y > c[x].max_count]
    if bad_cards:
        return deck_check_statuses[2], 'The following cards have too many copies of them: ' + ', ' .join(bad_cards)
    return deck_check_statuses[0], ''


def check_sideboard_size(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    card_count = sum([x for x in d.sideboard.values()])
    expected_size = 0 if 'EDH' in d.format.upper() or 'COMMANDER' in d.format.upper() else 15
    if card_count < expected_size:
        return deck_check_statuses[1], f'Too few sideboard cards: expected {expected_size}, got {card_count}'
    if card_count > expected_size:
        return deck_check_statuses[2], f'Too many sideboard cards: expected {expected_size}, got {card_count}'
    return deck_check_statuses[0], ''


def check_general_legality(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    bad = ['banned', 'not_legal']
    bad_cards = [x for x in d.mainboard if x not in c or c[x].legality.get(d.format, '') in bad]
    bad_sb_cards = [x + ' (sideboard)' for x in d.sideboard if x not in c or c[x].legality.get(d.format, '') in bad]
    if bad_cards or bad_sb_cards:
        return deck_check_statuses[2], 'The following cards are illegal: ' + ', '.join(bad_cards + bad_sb_cards)
    return deck_check_statuses[0], ''


def check_restricted_list(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    bad_cards = [x for x in chain(d.mainboard.keys(), d.sideboard.keys()) if x in c and
                 c[x].legality.get(d.format, '') == 'restricted' and d.mainboard.get(x, 0) + d.sideboard.get(x, 0) > 1]
    if bad_cards:
        return deck_check_statuses[2], 'The following cards are restricted but are present in more than 1 copy: ' + \
                                       ', '.join(bad_cards)
    return deck_check_statuses[0], ''
