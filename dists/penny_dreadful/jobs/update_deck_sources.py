import logging

from pymongo import UpdateMany

from shared.helpers.database import connect
from shared.types.competition import Competition

logger = logging.getLogger('dreadrise.dist.pd.sources')


def run() -> None:
    """
    Regenerate the sources of various PD decks, based on the competition data.
    :return: nothing
    """
    logger.info('Connecting...')
    client = connect('penny_dreadful')
    logger.info('Loading competitions...')
    comps = [Competition().load(x) for x in client.competitions.find({})]
    logger.info(f'{len(comps)} competitions loaded')

    actions = []
    for i in comps:
        actions.append(UpdateMany({'source': {'$exists': 0}, 'competition': i.competition_id},
                                  {'$set': {'source': i.type}}))
    client.decks.bulk_write(actions)
    logger.info('Operation complete.')
