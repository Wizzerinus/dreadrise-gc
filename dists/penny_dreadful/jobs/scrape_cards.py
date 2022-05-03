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
from ..constants import Formats, Update, pd_data
from ..custom_syntax import PDCard, PDCardFace

logger = logging.getLogger('dreadrise.dist.pd.card-scraper')
bad_sets = ['SLD', 'PLIST']
bad_colors = ['white', 'gold']
bad_statuses = ['missing', 'placeholder', 'lowres']
frame_effect_priority = {  # lower = more chance to be chosen
    'inverted': 1,
    'extendedart': 1,
    'etched': 2,
    'showcase': 3,
}


def get_priority(i: dict) -> int:
    # These cards shouldn't be in the database at all
    if i['lang'] != 'en' or i['legalities']['vintage'] in ['not_legal', 'banned']:
        return 0

    # These cards have lower priority
    priority = 1 + sum(frame_effect_priority.get(x, 0) for x in i.get('frame_effects', []))
    if len(i['set']) == 4 and i['set'][0].upper() == 'P':
        priority += 10
    if i['promo']:
        priority += 3
    if 'paper' not in i['games'] or 'mtgo' not in i['games']:
        priority += 200
    if i['set'].upper() in bad_sets:
        priority += 100
    if not i['booster']:
        priority += 1
    if i['border_color'] in bad_colors:
        priority += 50
    if 'flavor_name' in i:
        priority += 75
    if i['full_art']:
        priority += 1
    if i['image_status'] in bad_statuses:
        priority += 50
    if i['variation']:
        priority += 1

    return priority


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
    Update()
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
    data_with_priority = [(x, get_priority(x)) for x in data]
    data_with_priority = [x for x in data_with_priority if x[1]]
    for i, p in sorted(data_with_priority, key=lambda u: (-u[1], u[0]['released_at']), reverse=True):
        if i['name'] in cards:
            update_card(cards[i['name']], i)
        else:
            cards[i['name']] = cast(PDCard, build_card(i, Formats, fcs, PDCard, PDCardFace))

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
