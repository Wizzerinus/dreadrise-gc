import logging

from shared.helpers.caching.full_popularities import run_all_popularities
from shared.helpers.database import connect
from shared.types.caching import CardPlayability

logger = logging.getLogger('dreadrise.dist.pd.popularity')


def _postprocess_playability(cp: CardPlayability, fmt: str, full_deck_count: int) -> None:
    ratio = cp.deck_count / full_deck_count
    if ratio < 0.005:
        cp.playability = 'unplayed'
    elif ratio > 0.075:
        if cp.winrate > 0.55:
            cp.playability = 'good'
        else:
            cp.playability = 'staple'
    else:
        if cp.winrate > 0.55:
            cp.playability = 'playable'
        else:
            cp.playability = 'played'


def run() -> None:
    """
    Calculates the popularity of various PD cards.
    :return: nothing
    """
    logger.info('Connecting...')
    client = connect('penny_dreadful')
    run_all_popularities(client, _postprocess_playability)
