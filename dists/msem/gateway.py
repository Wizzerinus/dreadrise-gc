import logging
from threading import Thread
from traceback import print_exc
from typing import Dict

from pymongo.errors import OperationFailure

from shared.helpers.exceptions import DreadriseError, InvalidArgumentError
from shared.helpers.tagging.core import MaybeCC
from shared.types.card import Card

logger = logging.getLogger('dreadrise.gateway.msem')


def parse(data: dict) -> dict:
    try:
        if 'action' not in data:
            raise InvalidArgumentError('The request JSON must include the `action` field.')
        if data['action'] == 'update_cards':
            update_cards()
        elif data['action'] == 'create_competition':
            cache = create_competition(data)
            create_archetype_thread(cache)
        elif data['action'] == 'create_multiple_competitions':
            cache = None
            for i in data['objects']:
                cache = create_competition(i, card_cache=cache)
            create_archetype_thread(cache)
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


def create_competition(data: dict, card_cache: MaybeCC = None) -> Dict[str, Card]:
    from .jobs.scrape_decks import run_json

    logger.info('Updating decks...')
    data = run_json(data, False, card_cache=card_cache)
    logger.info('Update complete.')
    return data


def create_archetype_thread(card_cache: MaybeCC = None) -> None:
    from .jobs.calculate_popularities import run

    def run_with_cache() -> None:
        run(card_cache=card_cache)

    logger.info('Updating archetypes...')
    archetype_thread = Thread(target=run_with_cache)
    archetype_thread.start()
    logger.info('Update complete.')
