import logging
from time import sleep
from typing import Dict, cast

from shared import fetch_tools
from shared.helpers.card_engines.scryfall import build_card, build_expansion
from shared.helpers.database import connect
from shared.helpers.exceptions import RisingDataError
from shared.helpers.magic import get_rarity
from shared.types.card import Card
from shared.types.format_cache import FormatCache

from ..category import add_card_categories
from ..constants import formats, pd_data, update
from ..custom_syntax import PDCard, PDCardFace

logger = logging.getLogger('dreadrise.dist.pd.card-scraper')


def is_valid(i: dict) -> bool:
    return i['legalities']['vintage'] != 'not_legal' and i['lang'] == 'en' and \
        i['legalities']['vintage'] != 'banned' and \
        ((not i['promo'] and ('paper' in i['games'] or 'mtgo' in i['games']) and i['set'].upper() != 'SLD' and
         i['border_color'] not in ['borderless', 'gold'] and not i['full_art'] and not
          [x for x in ['etched', 'inverted', 'extendedart'] if x in i.get('frame_effects', [])]) or not i['reprint'])


def update_card(c: Card, i: Dict) -> None:
    rarity = get_rarity(i['rarity'])
    if rarity not in c.rarities:
        c.rarities.append(rarity)

    cset = i['set'].upper()
    if cset not in c.sets:
        c.sets.append(cset)


bulk_data_url = 'https://api.scryfall.com/bulk-data'
expansion_url = 'https://api.scryfall.com/sets'


def run() -> None:
    logger.info('Updating seasons')
    update()
    logger.info('Connecting to database')
    client = connect('penny_dreadful')
    logger.info('Loading legalities')
    fcs = [FormatCache().load(x) for x in client.format_cache.find()]
    logger.info(f'Loaded {len(fcs)} custom formats')
    logger.info('Loading bulk data')
    bulk_data = fetch_tools.fetch_json(bulk_data_url)

    card_url = ''
    logger.info('Looking for bulk cards')
    for i in bulk_data['data']:
        if i['type'] == 'default_cards':
            card_url = i['download_uri']
            break
    if not card_url:
        logger.info('Error: Bulk cards not found!')
        return

    logger.info('Loading default cards')
    data = fetch_tools.fetch_json(card_url)
    logger.info('Default cards loaded')

    cards: Dict[str, PDCard] = {}
    for i in sorted(data, key=lambda u: u['released_at'], reverse=True):
        if i['name'] in cards:
            update_card(cards[i['name']], i)
        elif is_valid(i):
            cards[i['name']] = cast(PDCard, build_card(i, formats, fcs, PDCard, PDCardFace))

            min_pd = max_pd = None
            for pdv in range(1, pd_data['last_season'] + 1):
                if cards[i['name']].legality[f'pds{pdv}'] != 'not_legal':
                    if not min_pd:
                        min_pd = pdv
                    max_pd = pdv

            if min_pd and max_pd:
                cards[i['name']].ftime = min_pd
                cards[i['name']].ltime = max_pd
    logger.info(f'{len(cards)} cards processed')

    logger.info('Loading expansions')
    data = fetch_tools.fetch_json(expansion_url)
    logger.info('Expansions loaded')
    expansions = [build_expansion(x) for x in data['data']]

    card_arr = []
    for i in cards.values():
        try:
            i.process()
            add_card_categories(i)
            card_arr.append(i)
        except RisingDataError as e:
            logger.error(f'Validation failed: {e}')

    logger.info(f'Processed {len(card_arr)} cards')
    logger.warning('DROPPING COLLECTION IN 5 SECONDS! Abort the script if it is not the desired outcome.')
    sleep(5)
    logger.warning('Starting the operation...')
    client.cards.delete_many({})
    client.cards.insert_many([x.save() for x in card_arr])
    logger.info('Inserted cards.')
    client.expansions.delete_many({})
    client.expansions.insert_many([x.save() for x in expansions])
    logger.info('Inserted expansions.')
