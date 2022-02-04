import logging
import traceback
from time import sleep
from typing import Dict, List

import arrow

from shared import fetch_tools
from shared.helpers.card_engines.cockatrice import process_cockatrice_set
from shared.helpers.database import connect
from shared.helpers.exceptions import DreadriseError, RisingDataError
from shared.types.set import Expansion

from ..category import add_card_categories
from ..custom_syntax import MSEMCard, MSEMCardFace

logger = logging.getLogger('dreadrise.dist.msem.card-scraper')
_msem_card_url = 'https://mse-modern.com/msem2/notlackey/AllSets.json'


def _get_image_url(set_id: str, card_dict: dict) -> str:
    num = card_dict['mciNumber']
    return f'https://mse-modern.com/msem2/images/{set_id}/{num}.jpg'


def _is_masterpiece(set_id: str) -> bool:
    return 'MPS' in set_id or set_id in {'MS1', 'MS2', 'MS3', 'L1', 'L2', 'L3', 'PLAY'}


exclusions = ['Velir, the Sunderer', 'Masahita, Bloodotongue', 'Acin, the Toymaker Avatar', 'Yatiri del Carnaval',
              'Small Gifts', 'Big Presents', 'Massive Surprises']


def process_sets(expansions: Dict[str, Expansion], sets: List[str]) -> List[str]:
    sets = list(set(sets))
    sets.sort(key=lambda x: expansions[x].release_date, reverse=True)
    return sets


def run() -> None:
    """
    Download the list of all MSEM cards from the server and saves them into the database.
    :return: nothing
    """
    logger.info('Scraping MSEM cards')
    data = fetch_tools.fetch_json(_msem_card_url)
    logger.info('{n} sets loaded'.format(n=len(data['data'])))

    try:
        cards = {}
        expansions = []
        for i in data['data'].values():
            set_id = i['code']
            if set_id == 'FLP' or set_id == 'LAIR':  # foreign language promos
                logger.info(f'Skipping {set_id}')
                continue
            cset, exp = process_cockatrice_set(i, _get_image_url, {'MSEM2': 'msem', 'MSEDH': 'msedh'},
                                               MSEMCard, MSEMCardFace)
            expansions.append(exp)
            set_date = arrow.get(i['releaseDate'])

            for card in cset:
                cname = card.faces[0].name
                if 'Conspiracy' in card.faces[0].types or cname in exclusions or 'Playtest' in cname:
                    continue

                card.release_date = set_date.datetime
                card_name = card.faces[0].name.split('_')[0]
                if card_name != card.faces[0].name or (
                    len(card.faces) > 1 and (card.faces[0].name == card.faces[1].name or not card.faces[1].name)
                ):
                    logger.info(f'Skipping a SL card {card.faces[0].name}')
                elif card_name not in cards:
                    logger.debug(f'New card: {card_name} in {set_id} ({card.faces[0].name})')
                    cards[card_name] = card
                elif set_date < cards[card_name].release_date:
                    if 'Basic' not in card.faces[0].types and not _is_masterpiece(set_id):
                        logger.info(f'Older card: {card_name} in {set_id}')
                    cards[card_name].sets.append(set_id)
                else:
                    if 'Basic' not in card.faces[0].types and not _is_masterpiece(set_id):
                        logger.info(f'Newer card: {card_name} in {set_id}')
                    old_sets = cards[card_name].sets
                    card.sets += old_sets
                    cards[card_name] = card

        expansion_dict = {x.code: x for x in expansions}
        card_arr = []
        for i in cards.values():
            try:
                i.sets = process_sets(expansion_dict, i.sets)
                i.process()
                add_card_categories(i)
                card_arr.append(i)
            except RisingDataError as e:
                logger.error(f'Validation failed: {e}')

        logger.info('Processed {n} cards'.format(n=len(card_arr)))
        logger.warning('DROPPING COLLECTION IN 5 SECONDS! Abort the script if it is not the desired outcome.')
        sleep(5)
        logger.warning('Starting the operation.')
        client = connect('msem')
        client.cards.delete_many({})
        client.cards.insert_many([x.save() for x in card_arr])
        logger.info('Inserted cards.')
        client.expansions.delete_many({})
        client.expansions.insert_many([x.save() for x in expansions])
        logger.info('Inserted expansions.')

    except (DreadriseError, KeyError, ValueError):
        logger.error('A error occured!')
        traceback.print_exc()
