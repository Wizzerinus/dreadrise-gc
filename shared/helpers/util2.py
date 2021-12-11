import logging
from importlib import import_module
from typing import List, Tuple, cast

from shared.core_enums import Distribution, distributions
from shared.types.deck import Deck
from shared.types.dist_constants import DistConstants

logger = logging.getLogger('dreadrise.util')


def build_deck(deck_list: List[Tuple[int, str, int, bool, int]]) -> Deck:  # Used with the deckbuilder
    d = Deck()
    d.mainboard = {y: x for x, y, _, z, _ in deck_list if not z}
    d.sideboard = {y: x for x, y, _, z, _ in deck_list if z}
    return d


def get_dist_constants(dist: Distribution) -> DistConstants:
    return cast(DistConstants, import_module(f'dists.{dist}.constants'))


def update_distributions() -> None:
    logger.info('Updating the distributions...')
    for i in distributions:
        if i != 'default':
            mod = import_module(f'dists.{i}.constants')
            try:
                mod.update()  # type: ignore
                logger.info(f'Updated {i}')
            except AttributeError:
                logger.info(f'Update function for {i} does not exist')
