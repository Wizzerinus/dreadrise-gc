import logging
from typing import Dict, List, Tuple

from shared.types.caching import CardPlayability
from shared.types.card import Card
from shared.types.deck import Deck

logger = logging.getLogger('dreadrise.popularity.playability')


def run_playability(fmt: str, g_cards: Dict[str, Card], g_decks: List[Deck]) -> List[CardPlayability]:
    decks_in_format = [x for x in g_decks if x.format == fmt] if fmt != '_all' else g_decks
    logger.info('Staple calculation: fast way')
    card_stuff = [(x, z.wins, z.losses) for z in decks_in_format for x in z.mainboard if x in g_cards]
    counter: Dict[str, CardPlayability] = {}
    wins_losses: Dict[str, Tuple[int, int]] = {}
    for card_name, wins, losses in card_stuff:
        cp = counter.get(card_name, None)
        if not cp:
            cp = CardPlayability()
            cp.format = fmt
            cp.card_name = card_name
            cp.deck_count = 0
            counter[card_name] = cp

        cp.deck_count += 1
        wl = wins_losses.get(card_name, (0, 0))
        wins_losses[card_name] = (wl[0] + wins, wl[1] + losses)

    for name, cp in counter.items():
        deck_wins, deck_losses = wins_losses[name]
        cp.winrate = deck_wins / max(1, deck_losses + deck_wins)

    return list(counter.values())
