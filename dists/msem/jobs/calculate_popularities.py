import logging

import arrow

from shared.helpers.caching.full_popularities import run_all_popularities
from shared.helpers.database import connect
from shared.helpers.tagging.core import MaybeCC, run_all_decks, run_new_decks
from shared.types.caching import CardPlayability
from shared.types.deck import Deck

logger = logging.getLogger('dreadrise.dist.msem.popularity')


def _timecheck(d: Deck) -> bool:
    return arrow.get(d.date).shift(months=3) > arrow.utcnow()


def _postprocess_playability(cp: CardPlayability, fmt: str, fmt_count: int) -> None:
    if cp.deck_count < 3:
        cp.playability = 'unplayed'
    elif cp.deck_count >= 8:
        if cp.winrate > 0.5:
            cp.playability = 'good'
        else:
            cp.playability = 'staple'
    else:
        if cp.winrate > 0.5:
            cp.playability = 'playable'
        else:
            cp.playability = 'played'


def run(card_cache: MaybeCC = None, only_new: bool = False) -> None:
    """
    Calculates the popularity of various MSEM cards.
    :return: nothing
    """
    logger.info('Connecting...')
    client = connect('msem')
    logger.info('Running the archetype calculator')
    func = run_new_decks if only_new else run_all_decks
    card_cache = func('msem', card_cache=card_cache)
    logger.info('Calculating popularities')
    run_all_popularities(client, _postprocess_playability, _timecheck, card_cache=card_cache)
