import logging
from typing import List

from shared import fetch_tools
from shared.helpers.database import connect

logger = logging.getLogger('dreadrise.dist.pd.format-loader')


def get_exceptions(code: str) -> List[str]:
    if code != 'EMN':
        return []
    return ['Séance', 'Lim-Dûl the Necromancer', 'Dandân', 'Jötun Grunt', 'Jötun Owl Keeper', 'Khabál Ghoul',
            'Lim-Dûl\'s Cohort', 'Lim-Dûl\'s High Guard', 'Ghazbán Ogre', 'Junún Efreet', 'Ifh-Bíff Efreet',
            'Ring of Ma\'rûf']


def run() -> None:
    logger.info('Connecting to database')
    client = connect('penny_dreadful')
    logger.info('Loading current formats')
    formats = fetch_tools.fetch_json('https://pennydreadfulmagic.com/api/seasoncodes')

    need_to_regenerate_pdsx = False
    for n, code in enumerate(formats):
        n += 1
        fmt = f'pds{n}'
        fc = client.format_cache.find_one({'format': fmt})
        if fc:
            logger.info(f'Season {n} already found, skipping')
            continue

        need_to_regenerate_pdsx = True
        logger.warning(f'Season {n} not found, downloading...')
        url = f'https://pennydreadfulmtg.github.io/{code}_legal_cards.txt'
        legal_list = [x for x in fetch_tools.fetch_str(url).replace('\r', '').split('\n') if x] + get_exceptions(code)
        client.format_cache.insert({'format': fmt, 'legal': legal_list, 'restricted': [], 'banned': []})
        logger.warning(f'Processed season {n}, {len(legal_list)} legal cards')

    if need_to_regenerate_pdsx:
        logger.warning('Regenerating PD Eternal')
        client.format_cache.delete_one({'format': 'pdsx'})
        fcs = client.format_cache.find()
        legal_cards = {x for y in fcs for x in y['legal']}
        client.format_cache.insert({'format': 'pdsx', 'legal': list(legal_cards), 'restricted': [], 'banned': []})
        logger.warning(f'PD Eternal finished, {len(legal_cards)} legal cards')

    logger.info('Format caches saved.')
