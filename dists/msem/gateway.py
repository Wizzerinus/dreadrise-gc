import logging
from threading import Thread
from traceback import print_exc

from pymongo.errors import OperationFailure

from shared.helpers.exceptions import DreadriseError, InvalidArgumentError

logger = logging.getLogger('dreadrise.gateway.msem')


def parse(data: dict) -> dict:
    try:
        if 'action' not in data:
            raise InvalidArgumentError('The request JSON must include the `action` field.')
        if data['action'] == 'update_cards':
            update_cards()
        elif data['action'] == 'create_competition':
            create_competition(data)
            create_archetype_thread()
        elif data['action'] == 'create_multiple_competitions':
            for i in data['objects']:
                create_competition(i)
            create_archetype_thread()
        else:
            raise InvalidArgumentError('Invalid action: ' + data['action'])

        return {'success': True}
    except (KeyError, ValueError, AttributeError, DreadriseError, OperationFailure) as e:
        logger.error('Gateway call errored!')
        print_exc()
        return {'success': False, 'reason': str(e)}


def update_cards() -> None:
    from .jobs.scrape_cards import run
    logger.info('Updating cards...')
    run()
    logger.info('Update complete.')


def create_competition(data: dict) -> None:
    from .jobs.scrape_decks import run_json

    logger.info('Updating decks...')
    run_json(data, False)
    logger.info('Update complete.')


def create_archetype_thread() -> None:
    from .jobs.calculate_popularities import run

    logger.info('Updating archetypes...')
    archetype_thread = Thread(target=run)
    archetype_thread.start()
    logger.info('Update complete.')
