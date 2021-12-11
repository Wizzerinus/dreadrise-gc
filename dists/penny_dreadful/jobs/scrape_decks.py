import logging
from datetime import datetime
from functools import reduce
from math import ceil
from time import sleep
from typing import Dict, List, Set, Tuple, cast

import arrow
from pymongo.database import Database

from shared import fetch_tools
from shared.card_enums import Archetype
from shared.helpers.database import connect
from shared.helpers.util import clean_name
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag
from shared.types.user import User, UserPrivileges

logger = logging.getLogger('dreadrise.dist.pd.deck-scraper')
pdm_host = 'https://pennydreadfulmagic.com'
page_size = 300


def init() -> Database:
    logger.info('Connecting to database')
    return connect('penny_dreadful')


def get_deck(d: List[dict]) -> Dict[str, int]:
    return {x['name']: x['n'] for x in d}


def get_competition(name: str) -> Tuple[str, str]:
    replacements = [('Penny Dreadful', 'PD'), ('Championships', 'CS'), ('Championship', 'CS'),
                    ('Tournament of Champions', 'Final'), ('Season ', 'S')]
    name = reduce(lambda a, kv: a.replace(*kv), replacements, name)
    if 'Kick Off' in name or 'Kickoff' in name:
        ctype = 'kickoff'
    elif '500' in name or 'CS' in name or 'Final' in name:
        ctype = 'pd500'
    elif 'League' not in name:
        ctype = 'tournament'
    else:
        ctype = 'league'
    return name, ctype


def obtain_deck(d: Dict, fd: arrow.arrow.Arrow) -> Deck:
    dk = Deck()

    dk.deck_id = 'pdm-' + str(d['id'])
    dk.name = d['name']
    dk.is_name_placeholder = False
    dk.author = str(d['personId'])
    season = d['seasonId']
    dk.competition = str(d['competitionId'] or f'cseason-{season}')
    dk.format = f'pds{season}'
    dk.date = datetime.fromtimestamp(d['activeDate'])

    cname, ct = get_competition(d['competitionName'])
    if ct == 'tournament':
        time_delta = arrow.get(dk.date) - fd
        week_num = time_delta.days // 7 + 1
        dk.competition = f'tourney-{season}-{week_num}'
    else:
        dk.competition = str(d['competitionId'])

    dk.tags = [clean_name(d['archetypeName'])]
    dk.is_sorted = True

    dk.mainboard = get_deck(d['maindeck'])
    dk.sideboard = get_deck(d['sideboard'])
    dk.games = []
    dk.wins = d['wins']
    dk.losses = d['losses']
    dk.ties = d.get('ties', 0)
    dk.privacy = 'public'

    return dk


def check_deck_filter(x: dict) -> bool:
    return x['reviewed'] and x['archetypeName'] and x['sorted'] and x['archetypeName'] != 'Unclassified' and \
        (x['sourceName'] == 'League' or x['sourceName'] == 'Gatherling') and x['wins'] + x['losses'] > 0


def obtain_decks(existing_decks: Set[int], decks: List[Dict], fd: arrow.arrow.Arrow) -> List[Deck]:
    ans = []
    for x in decks:
        if not check_deck_filter(x) or x['id'] in existing_decks:
            continue
        existing_decks.add(x['id'])

        obtained = obtain_deck(x, fd)
        ans.append(obtained)
    return ans


def obtain_comps(existing_comps: Dict[str, Competition], decks: List[Dict], fd: arrow.arrow.Arrow) -> List[Competition]:
    ans = []
    for x in decks:
        if not check_deck_filter(x):
            continue

        season = x['seasonId']
        cname, ctype = get_competition(x['competitionName'] or f'PD Season {season}')
        if ctype == 'tournament':
            time_delta = arrow.get(x['activeDate']) - fd
            week_num = time_delta.days // 7 + 1
            comp = f'tourney-{season}-{week_num}'
            cname = f'S{season} tournaments - week {week_num}'
        else:
            comp = str(x['competitionId'])
        if comp in existing_comps:
            continue

        new_comp = Competition()
        new_comp.competition_id = comp
        new_comp.format = f'pds{season}'
        new_comp.date = datetime.fromtimestamp(x['activeDate'])
        new_comp.name, new_comp.type = cname, ctype
        existing_comps[comp] = new_comp
        ans.append(new_comp)
    return ans


def obtain_users(existing_users: Dict[str, User], decks: List[Dict]) -> List[User]:
    ans = []
    for x in decks:
        user_id = str(x['personId'])
        if user_id in existing_users:
            continue

        new_user = User()
        new_user.user_id = user_id
        new_user.nickname = x['person']
        if x['discordId']:
            new_user.login = 'discord.' + str(x['discordId'])
        new_user.privileges = UserPrivileges()
        existing_users[user_id] = new_user
        ans.append(new_user)
    return ans


def get_min_date(decks: List[dict]) -> arrow.arrow.Arrow:
    return arrow.get(min((x['activeDate'] for x in decks)))


def load_all(existing_users: Dict[str, User], existing_competitions: Dict[str, Competition], url: str) -> \
        Tuple[List[Deck], List[User], List[Competition]]:
    logger.info(f'Loading from {url}0')
    initial_load = fetch_tools.fetch_json(pdm_host + url + '0')
    entries = initial_load['total']
    deck_arr = initial_load['objects']
    pages = ceil(entries / page_size)
    logger.info(f'Found {entries} entries, loading {pages - 1} extra pages')

    existing_decks: Set[int] = set()
    for i in range(1, pages):
        sleep(1)
        logger.info(f'Loading page {i}')
        new_page = fetch_tools.fetch_json(pdm_host + url + str(i))
        deck_arr += new_page['objects']

    first_date = get_min_date(deck_arr)
    decks = obtain_decks(existing_decks, deck_arr, first_date)
    comps = obtain_comps(existing_competitions, deck_arr, first_date)
    users = obtain_users(existing_users, deck_arr)
    return decks, users, comps


def run_all_decks(season_num: str) -> None:
    client = init()
    logger.warning(f'Deleting everything related to season {season_num} in 5 seconds!')
    # sleep(5)
    client.decks.delete_many({'format': f'pds{season_num}'})
    client.competitions.delete_many({'format': f'pds{season_num}'})
    logger.warning('Purging complete')
    logger.info('Loading users')
    all_users = {x['user_id']: User().load(x) for x in client.users.find()}
    logger.info('Loading PDM')
    decks, users, comps = load_all(all_users, {},
                                   f'/api/decks/?deckType=all&pageSize={page_size}&seasonId={season_num}&page=')
    if decks:
        logger.info(f'Inserting {len(decks)} decks...')
        client.decks.insert_many([x.save() for x in decks])
    if users:
        logger.info(f'Inserting {len(users)} users...')
        client.users.insert_many([x.save() for x in users])
    if comps:
        logger.info(f'Inserting {len(comps)} competitions...')
        client.competitions.insert_many([x.save() for x in comps])
    logger.info('Operation complete.')


def run_archetypes() -> None:
    client = init()
    logger.info('Loading archetypes')
    arch_load = fetch_tools.fetch_json(f'{pdm_host}/api/archetypes')

    logger.info('Parsing archetypes')
    archetype_tree: Dict[str, str] = {}
    archetype_output = []

    remaining_archetypes = arch_load['objects']
    depth = 0  # OH NO!
    while remaining_archetypes:
        depth += 1
        bad_tags = []
        for i in remaining_archetypes:
            new_tag = DeckTag()
            new_tag.name = i['name']
            new_tag.tag_id = clean_name(i['name'])

            if i['ancestor'] and i['ancestor'] not in archetype_tree:
                bad_tags.append(i)
            else:
                archetype_tree[new_tag.name] = archetype_tree[i['ancestor']] if i['ancestor'] else new_tag.tag_id
                new_tag.archetype = cast(Archetype, archetype_tree[new_tag.name])
                new_tag.description = 'No description'
                archetype_output.append(new_tag)
        remaining_archetypes = bad_tags
        if depth > 10:
            logger.error('These archetypes are remaining: %s', bad_tags)
            return

    logger.info(f'Generated {len(archetype_output)} archetypes, inserting...')
    logger.warning('Deleting all archetypes in 5 seconds!')
    sleep(5)
    client.deck_tags.delete_many({})
    logger.warning('Purging complete')
    client.deck_tags.insert_many([x.save() for x in archetype_output])
    logger.info('Operation complete.')
