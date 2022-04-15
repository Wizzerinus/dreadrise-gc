import logging
import re
from typing import Dict, List

from shared.helpers.database import connect
from shared.types.card import Card
from shared.types.set import Expansion

from ..constants import Formats

logger = logging.getLogger('dreadrise.dist.fusion.card-scraper')

exact_checks = []
reminder_regex = re.compile(r' \((.+?)\)')


def remove_pd(card: Card) -> dict:
    card.legality = {x: y for x, y in card.legality.items() if x in Formats}
    for i in Formats:
        if i not in card.legality:
            card.legality[i] = 'not_legal'
    card.legality['hybrid'] = 'legal'

    ans = card.save()
    ans['database'] = 'canon'
    for x in ['ftime', 'ltime']:
        if x in ans:
            del ans[x]
    return ans


def remove_msem(card: Card) -> dict:
    card.legality = {x: y for x, y in card.legality.items() if x in Formats}
    for i in Formats:
        if i not in card.legality:
            card.legality[i] = 'not_legal'
    card.legality['hybrid'] = 'legal'

    ans = card.save()
    ans['database'] = 'custom'
    return ans


def merge(dict1: Dict[str, dict], dict2: Dict[str, dict]) -> List[dict]:
    for i, j in dict2.items():
        if i in dict1:
            dict1[i]['sets'] += j['sets']
            for u, v in j['legality'].items():
                if v != 'not_legal':
                    dict1[i]['legality'][u] = v

            exact_checks.append((dict1[i], j))
        else:
            dict1[i] = j
    return list(dict1.values())


def print_card(card: dict) -> str:
    name, cost, oracle = card['name'], card['mana_cost_str'], card['oracle']
    oracle = reminder_regex.sub('', oracle)
    return f'{name} {cost}\n{oracle}'


def check_exactness(expansions: Dict[str, Expansion]) -> None:
    for canon, custom in exact_checks:
        canon_text = print_card(canon).strip()
        custom_text = print_card(custom).strip()
        if canon_text == custom_text:
            continue

        canon_exp = [expansions[x] for x in canon['sets'] if x not in custom['sets']]
        custom_exp = [expansions[x] for x in custom['sets']]
        canon_date = min(u.release_date for u in canon_exp)
        custom_date = min(u.release_date for u in custom_exp)
        if canon_date < custom_date:
            print('WARNING!')

        print(f'Canon date: {canon_date} | Custom date: {custom_date}')
        print('Canon:', canon_text)
        print('Custom:', custom_text)
        print('')


def run() -> None:
    logger.info('Connecting to databases')
    client_sc = connect('fusion')
    client_pd = connect('penny_dreadful')
    client_msem = connect('msem')

    logger.info('Loading expansions')
    expansions_pd = [x for x in client_pd.expansions.find()]
    expansions_msem = [x for x in client_msem.expansions.find()]
    expansions = expansions_msem + expansions_pd
    logger.info(f'Found {len(expansions)} expansions, inserting...')
    client_sc.expansions.delete_many({})
    client_sc.expansions.insert_many(expansions)
    logger.info('Expansions inserted.')

    logger.info('Loading cards')
    cards_pd = {x['card_id']: remove_pd(Card().load(x)) for x in client_pd.cards.find()}
    cards_msem = {x['card_id']: remove_msem(Card().load(x)) for x in client_msem.cards.find()}
    cards = merge(cards_pd, cards_msem)
    logger.info(f'Found {len(cards)} cards, inserting...')
    client_sc.cards.delete_many({})
    client_sc.cards.insert_many(cards)
    logger.info('Cards inserted.')
    # logger.info('Checking exact matches.')
    # check_exactness({x['code']: Expansion().load(x) for x in expansions})
