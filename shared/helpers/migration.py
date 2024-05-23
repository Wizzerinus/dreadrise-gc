import logging

from pymongo import UpdateOne

from shared.core_enums import Distribution
from shared.helpers.database import connect
from shared.helpers.util2 import calculate_color_data
from shared.types.card import Card
from shared.types.deck import Deck

logger = logging.getLogger('dreadrise.migration')


def run_migration(dist: Distribution) -> None:
    db = connect(dist)
    logger.info('Loading cards...')
    cards: dict[str, Card] = {x['name']: Card().load(x) for x in db.cards.find()}
    logger.info('Loading decks...')
    decks: dict[str, Deck] = {x['deck_id']: Deck().load(x) for x in db.decks.find()}
    logger.info(f'{len(decks)} decks loaded.')

    operation = []
    for i, j in decks.items():
        if j.color_data:
            continue
        operation.append(UpdateOne({'deck_id': i}, {'$set': {'color_data': calculate_color_data(j, cards)}}))
    logger.info(f'Calculated {len(operation)} operations.')
    if operation:
        db.decks.bulk_write(operation)
        logger.info('Operation complete.')
    else:
        logger.info('Nothing to do.')
