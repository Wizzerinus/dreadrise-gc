import logging
from datetime import datetime
from functools import reduce
from math import ceil
from time import sleep
from typing import Dict, Iterable, List, Set, Tuple, Union, cast

from arrow import Arrow, get
from pymongo import UpdateMany
from pymongo.database import Database

from shared import fetch_tools
from shared.card_enums import Archetype
from shared.helpers.database import connect
from shared.helpers.exceptions import FetchError
from shared.helpers.util import clean_name
from shared.helpers.util2 import calculate_color_data
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck, DeckGameRecord
from shared.types.deck_tag import DeckTag
from shared.types.user import User, UserPrivileges

from ..constants import Update, pd_data

logger = logging.getLogger('dreadrise.dist.pd.deck-scraper')
pdm_host = 'https://pennydreadfulmagic.com'
page_size = 100
match_page_size = 200


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


def obtain_deck(d: Dict, fd: Arrow, cards: Dict[str, Card]) -> Deck:
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
        time_delta = get(dk.date) - fd
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
    dk.color_data = calculate_color_data(dk, cards)

    return dk


def check_deck_filter(x: dict) -> bool:
    return x['reviewed'] and x['archetypeName'] and x['sorted'] and x['archetypeName'] != 'Unclassified' and \
        (x['sourceName'] == 'League' or x['sourceName'] == 'Gatherling') and x['wins'] + x['losses'] > 0


def obtain_decks(existing_decks: Set[int], decks: List[Dict], fd: Arrow, cards: Dict[str, Card]) -> Dict[int, Deck]:
    ans = {}
    for x in decks:
        if not check_deck_filter(x) or x['id'] in existing_decks:
            continue
        existing_decks.add(x['id'])

        obtained = obtain_deck(x, fd, cards)
        ans[x['id']] = obtained
    return ans


def obtain_comps(existing_comps: Dict[str, Competition], decks: List[Dict], fd: Arrow) -> List[Competition]:
    ans = []
    for x in decks:
        if not check_deck_filter(x):
            continue

        season = x['seasonId']
        cname, ctype = get_competition(x['competitionName'] or f'PD Season {season}')
        if ctype == 'tournament':
            time_delta = get(x['activeDate']) - fd
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


def obtain_users(existing_users: Dict[str, User], decks: List[Dict], user_logins: Dict[str, str]) -> \
        Tuple[List[User], Dict[str, str]]:
    ans = {}
    removals = {}
    for x in decks:
        user_id = str(x['personId'])
        if user_id in existing_users:
            continue

        new_user = User()
        new_user.user_id = user_id
        new_user.nickname = x['person']
        if x['discordId']:
            new_user.login = 'discord.' + str(x['discordId'])
            if (old_user_id := user_logins.get(new_user.login, user_id)) != user_id:
                logger.warning(f'Duplicate login: {new_user.login}')
                existing_users[old_user_id] = User()
                ans.pop(old_user_id, None)
                removals[old_user_id] = user_id

        new_user.privileges = UserPrivileges()
        existing_users[user_id] = new_user
        ans[user_id] = new_user
    return list(ans.values()), removals


def get_min_date(decks: List[dict]) -> Arrow:
    return get(min((x['activeDate'] for x in decks)))


def load_all(existing_users: Dict[str, User], existing_competitions: Dict[str, Competition], url: str) -> \
        Tuple[Dict[int, Deck], List[User], List[Competition], Dict[str, str]]:
    db = connect('penny_dreadful')
    logger.info('Loading cards')
    cards = {x['name']: Card().load(x) for x in db.cards.find()}
    logger.info(f'Loading from {url}')
    initial_load = fetch_tools.fetch_json(pdm_host + url + '0')
    entries = initial_load['total']
    deck_arr = initial_load['objects']
    pages = ceil(entries / page_size)
    logger.info(f'Found {entries} decks, loading {pages - 1} extra pages')

    existing_decks: Set[int] = set()
    for i in range(1, pages):
        sleep(0.5)
        logger.info(f'Loading page {i}')
        try:
            new_page = fetch_tools.fetch_json(pdm_host + url + str(i))
        except FetchError as e:
            if '502' in str(e):
                logger.warning('We are being rate-limited. Sleeping for 10 seconds.')
                sleep(10)
                new_page = fetch_tools.fetch_json(pdm_host + url + str(i))
            else:
                logger.error(f'Failed to load page {i}!')
                raise e

        deck_arr += new_page['objects']

    first_date = get_min_date(deck_arr)
    decks = obtain_decks(existing_decks, deck_arr, first_date, cards)
    comps = obtain_comps(existing_competitions, deck_arr, first_date)
    users, removed_users = obtain_users(existing_users, deck_arr,
                                        {user.login: user_id for user_id, user in existing_users.items()})
    return decks, users, comps, removed_users


def inject_single_match(deck: Deck, record: Dict, not_opponent: bool) -> None:
    dgr = DeckGameRecord()
    odi_base = record['opponentDeckId'] if not_opponent else record['deckId']
    if odi_base:
        dgr.opposing_deck_id = 'pdm-' + str(odi_base)
    dgr.player_wins = record['gameWins'] if not_opponent else record['gameLosses']
    dgr.player_losses = record['gameLosses'] if not_opponent else record['gameWins']
    dgr.result = dgr.player_wins >= 2
    if record['elimination']:
        dgr.round = 'QF' if record['elimination'] == 8 else ('SF' if record['elimination'] == 4 else 'F')
    deck.games.append(dgr)


def inject_single_bye(deck: Deck, record: Dict) -> None:
    dgr = DeckGameRecord()
    dgr.opposing_deck_id = ''
    dgr.player_wins = 2
    dgr.player_losses = 0
    dgr.result = True
    if record['elimination']:
        dgr.round = 'QF' if record['elimination'] == 8 else ('SF' if record['elimination'] == 4 else 'F')
    deck.games.append(dgr)


def inject_matches_from(decks: Dict[int, Deck], objects: Iterable[Dict]) -> None:
    for i in objects:
        deck_id, opponent_deck_id = i['deckId'], i['opponentDeckId']
        if deck_id and deck_id not in decks:
            logger.warning(f'Deck {deck_id} not found')
        elif not deck_id:
            inject_single_bye(decks[deck_id], i)
        else:
            inject_single_match(decks[deck_id], i, True)

        if opponent_deck_id not in decks:
            if opponent_deck_id:
                logger.warning(f'Deck {opponent_deck_id} not found')
        else:
            inject_single_match(decks[opponent_deck_id], i, False)


def inject_matches(decks: Dict[int, Deck], base_url: str) -> None:
    initial_load = fetch_tools.fetch_json(pdm_host + base_url + '0')
    entries = initial_load['total']
    sample = initial_load['objects']
    pages = ceil(entries / match_page_size)
    logger.info(f'Found {entries} matches, loading {pages - 1} extra pages')

    for i in range(1, pages):
        sleep(0.25)
        logger.info(f'Loading page {i}')
        new_page = fetch_tools.fetch_json(pdm_host + base_url + str(i))
        sample += new_page['objects']

    sorted_sample = sorted(sample, key=lambda a: (a['date'] or 0, a['round'] or 0))
    inject_matches_from(decks, sorted_sample)


def run_all_decks(season_num: Union[int, str]) -> None:
    client = init()
    logger.info('Loading users')
    all_users = {x['user_id']: User().load(x) for x in client.users.find()}
    logger.info('Loading PDM')
    decks, users, comps, user_removals = load_all(
        all_users, {}, f'/api/decks/?deckType=all&pageSize={page_size}&seasonId={season_num}&page=')
    logger.info('Finished loading decks, loading matches')
    inject_matches(decks, f'/api/matches/?pageSize={match_page_size}&seasonId={season_num}&page=')
    logger.warning(f'Deleting everything related to season {season_num} in 5 seconds!')
    sleep(5)
    client.decks.delete_many({'format': f'pds{season_num}', 'competition': {'$exists': 1}})
    client.competitions.delete_many({'format': f'pds{season_num}'})
    logger.warning('Purging complete')
    if decks:
        logger.info(f'Inserting {len(decks)} decks...')
        client.decks.insert_many([x.save() for x in decks.values()])
    if users:
        if user_removals:
            logger.warning(f'Filtering out duplicate users (found {len(user_removals)})...')
            client.users.delete_many({'user_id': {'$in': list(user_removals.keys())}})
            # then we need to replace the user ids in the deck entries... pain
            operations = [UpdateMany({'author': user_id}, {'$set': {'author': new_id}})
                          for user_id, new_id in user_removals.items()]
            client.decks.bulk_write(operations)
        logger.info(f'Inserting {len(users)} users...')
        client.users.insert_many([x.save() for x in users])
    if comps:
        logger.info(f'Inserting {len(comps)} competitions...')
        client.competitions.insert_many([x.save() for x in comps])
    logger.info('Operation complete.')


def run_all_seasons(min_season: int = 1) -> None:
    logger.info('Loading seasons')
    Update()
    last_season = pd_data['last_season']
    if not last_season:
        logger.error('PDM is down, aborting')
        return

    for i in range(min_season, last_season + 1):
        logger.info(f'Working on season {i}')
        run_all_decks(i)


def run_last_season() -> None:
    logger.info('Loading seasons')
    Update()
    last_season = pd_data['last_season']
    if not last_season:
        logger.error('PDM is down, aborting')
        return

    logger.info(f'Working on season {last_season}')
    run_all_decks(last_season)


def run_archetypes() -> None:
    client = init()
    logger.info('Loading archetypes')
    arch_load = fetch_tools.fetch_json(f'{pdm_host}/api/archetypes')

    logger.info('Parsing archetypes')
    archetype_tree: Dict[str, str] = {}
    archetype_output = []

    remaining_archetypes = arch_load['objects']
    reverse_tree: Dict[str, List[str]] = {}
    tree_paths: Dict[str, List[str]] = {}
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

                if i['ancestor']:
                    cl_anc = clean_name(i['ancestor'])
                    if cl_anc not in reverse_tree:
                        reverse_tree[cl_anc] = []
                    reverse_tree[cl_anc].append(new_tag.tag_id)
                    tree_paths[new_tag.tag_id] = tree_paths[cl_anc] + [new_tag.tag_id]
                else:
                    tree_paths[new_tag.tag_id] = [new_tag.tag_id]
        remaining_archetypes = bad_tags
        if depth > 10:
            logger.error('These archetypes are remaining: %s', bad_tags)
            return

    for i in archetype_output:
        i.parents = tree_paths[i.tag_id]
    logger.info(f'Generated {len(archetype_output)} archetypes, inserting...')
    logger.warning('Deleting all archetypes in 5 seconds!')
    sleep(5)
    client.deck_tags.delete_many({})
    logger.warning('Purging complete')
    client.deck_tags.insert_many([x.save() for x in archetype_output])
    logger.info('Operation complete.')
