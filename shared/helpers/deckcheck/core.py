from typing import Callable, Dict, List, Literal, Tuple, get_args

from shared.core_enums import Distribution
from shared.helpers.db_loader import load_cards_from_decks
from shared.types.card import Card
from shared.types.deck import Deck

DeckCheckStatus = Literal['Success!', 'Warnings found!', 'Errors found!']
deck_check_statuses: Tuple[DeckCheckStatus, ...] = get_args(DeckCheckStatus)


def deck_check(dist: Distribution, d: Deck,
               checkers: List[Callable[[Deck, Dict[str, Card]], Tuple[DeckCheckStatus, str]]]) -> \
        Tuple[DeckCheckStatus, List[str], List[str], List[str]]:
    errors = []
    warnings = []
    messages = []
    cards = load_cards_from_decks(dist, [d])

    for x in checkers:
        status, response = x(d, cards)
        if status == deck_check_statuses[2]:
            errors.append(response)
        elif status == deck_check_statuses[1]:
            warnings.append(response)
        elif response:
            messages.append(response)

    if errors:
        return deck_check_statuses[2], errors, warnings, messages
    elif warnings:
        return deck_check_statuses[1], [], warnings, messages
    else:
        return deck_check_statuses[0], [], [], messages
