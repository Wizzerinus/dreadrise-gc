import logging
from threading import Thread
from traceback import print_exc

from pymongo.errors import OperationFailure

from shared.helpers.exceptions import DreadriseError, InvalidArgumentError

logger = logging.getLogger('dreadrise.gateway.pd')


def parse(data: dict) -> dict:
    try:
        if 'action' not in data:
            raise InvalidArgumentError('The request JSON must include the `action` field.')
        if data['action'] == 'git_pull':
            git_pull()
        elif data['action'] == 'update_cards':
            scrape_cards()
        elif data['action'] == 'rotate':
            rotate()
        else:
            raise InvalidArgumentError('Invalid action: ' + data['action'])

        return {'success': True}
    except (KeyError, ValueError, AttributeError, DreadriseError, OperationFailure, FileNotFoundError) as e:
        logger.error('Gateway call errored!')
        print_exc()
        return {'success': False, 'reason': str(e)}


def git_pull() -> None:
    from .jobs.update_prod import run
    logger.info('Pulling the prod changes...')
    run()
    logger.info('Update complete.')


def scrape_cards() -> None:
    from .jobs.scrape_cards import run
    logger.info('Scraping cards...')
    card_thread = Thread(target=run)
    card_thread.start()
    logger.info('Scraping complete.')


def rotate() -> None:
    from .jobs.generate_format import run as run_gf
    from .jobs.scrape_cards import run as run_sc
    logger.info('Rotating...')

    def rotate_call() -> None:
        run_gf()
        run_sc()

    rotate_thread = Thread(target=rotate_call)
    rotate_thread.start()
    logger.info('Rotation complete.')
