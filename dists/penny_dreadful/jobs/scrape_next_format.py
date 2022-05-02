import logging
from math import ceil
from time import sleep

from shared import fetch_tools
from shared.helpers.database import connect

logger = logging.getLogger('dreadrise.dist.pd.next-format')
pdm_host = 'https://pennydreadfulmagic.com'
page_size = 400
skip = 0.5


def run() -> None:
    url_base = f'/api/rotation/cards/?pageSize={page_size}&page='
    logger.info(f'Loading from {url_base}')
    initial_load = fetch_tools.fetch_json(pdm_host + url_base + '0')
    entries = initial_load['total']
    card_arr = initial_load['objects']
    pages = ceil(entries / page_size)
    logger.info(f'Found {entries} cards, loading {pages - 1} extra pages')

    for i in range(1, pages):
        sleep(skip)
        logger.info(f'Loading page {i}')
        new_page = fetch_tools.fetch_json(pdm_host + url_base + str(i))
        card_arr += new_page['objects']

    ans = [{'name': x['name'], 'checks': x['hits']} for x in card_arr]
    logger.info('Converted to the correct format')
    db = connect('penny_dreadful')
    db.next_counts.delete_many({})
    db.next_counts.insert_many(ans)
    logger.info('Insertion complete.')
