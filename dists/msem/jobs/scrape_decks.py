import logging
import traceback
from time import sleep
from typing import Dict, Optional

import arrow
from pymongo.database import Database

from shared import fetch_tools
from shared.helpers.database import connect
from shared.helpers.exceptions import DreadriseError
from shared.helpers.util import clean_card, clean_name, shorten_name
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck, DeckGameRecord

logger = logging.getLogger('dreadrise.dist.msem.deck-scraper')
_competition_file_path = 'file:///home/wizzerinus/Documents/MSEM/league-oct-2021.json'


def _create_user(db: Database, username: str, user_discord: Optional[int]) -> str:
    u = db.users.find_one({'nickname': username})
    if u:
        logger.info(f'User {username} already exists')
        return u['user_id']

    user_id = clean_name(username)

    if user_discord:
        login = f'discord.{user_discord}'
        u = db.users.find_one({'login': login})
        if u:
            logger.info(f'Discord-user {username} already exists')
            return u['user_id']

        db.users.insert_one({
            'login': login,
            'nickname': username,
            'user_id': user_id,
            'privileges': {}
        })
        logger.warning(f'Creating discord-user for {username}')
    else:
        db.users.insert_one({
            'nickname': username,
            'user_id': user_id,
            'privileges': {}
        })
        logger.warning(f'Creating user without Discord for {username}')
    return user_id


def get_match(x: dict, position: int) -> DeckGameRecord:
    dg = DeckGameRecord()
    opposing_uid = x['players'][1 - position]['list']
    dg.opposing_deck_id = opposing_uid if opposing_uid and 'bye' not in opposing_uid.lower() else None
    dg.player_wins = int(x['players'][position]['wins'])
    dg.player_losses = int(x['players'][position]['losses'])
    # dg.winner = bool(x['players'][position]['victor' if 'victor' in x['players'][position] else 'winner'])
    dg.result = 0 if dg.player_losses == dg.player_wins else (1 if dg.player_wins > dg.player_losses else -1)
    return dg


def _build_deck_record(deck: Deck, matches: list, uid: str) -> None:
    first_matches = [(k, get_match(x, 0)) for k, x in enumerate(matches) if 'list' in x['players'][0] and
                     x['players'][0]['list'] == uid]
    second_matches = [(k, get_match(x, 1)) for k, x in enumerate(matches) if 'list' in x['players'][1] and
                      x['players'][1]['list'] == uid]
    all_games = first_matches + second_matches
    deck.games = [x[1] for x in sorted(all_games)]
    deck.wins = len([x for x in all_games if x[1].result == 1])
    deck.losses = len([x for x in all_games if x[1].result == -1])
    deck.ties = len([x for x in all_games if x[1].result == 0])


def smart_clean(name: str, cards: Dict[str, Card]) -> str:
    name = clean_card(name)
    if name not in cards:
        logger.error(f'Card {name} not found')
        return name
    return cards[name].name


def run() -> None:
    """
    Downloads a MSEM competition from the server and saves them into the database.
    :return: nothing
    """

    logger.info('Connecting to the database')
    client = connect('msem')
    logger.info('Loading cards')
    init_cards = {x['name']: Card().load(x) for x in client.cards.find({})}
    all_cards = {}
    for k, v in init_cards.items():
        all_cards[k] = v
        if len(v.faces) > 1:
            for f in v.faces:
                all_cards[f.name] = v
            all_cards[' // '.join([x.name for x in v.faces])] = v
    logger.info('Scraping MSEM decks')
    json = fetch_tools.fetch_json(_competition_file_path)
    logger.info('{n} decks, {m} matches loaded'.format(n=len(json['decks']), m=len(json['matches'])))

    try:
        comp_name, date, decks, matches = json['competition_name'], json['date'], json['decks'], json['matches']
        date_object = arrow.get('20' + date.replace('_', '-')).datetime

        old_comp = client.competitions.find_one({'name': comp_name})
        # comp = Competition.objects(name=comp_name).first()
        if old_comp:
            logger.warning(f'Deleting {comp_name} in 5 seconds!')
            sleep(5)
            client.competitions.delete_one({'name': comp_name})
            client.decks.delete_many({'competition': clean_name(comp_name)})
            logger.warning(f'Deleted {comp_name}.')

        comp = Competition()
        comp.competition_id = clean_name(comp_name)
        comp.name = comp_name
        comp.format = 'msem'
        comp.type = 'gp' if 'GP' in comp_name or 'Grand Prix' in comp_name else 'league'
        comp.date = date_object
        client.competitions.insert_one(comp.save())
        logger.info('Created the competition')

        for m in matches:
            for u in m['players']:
                if 'list' in u:
                    u['list'] = clean_name(u['list'][1:].replace('.txt', ''))
        logger.info('Parsed matches')

        decks_by_id = {}
        for item in decks:
            deckname, cards, deck_id = item['name'] if 'name' in item else 'No name', item['cards'], item['deck_id']
            discord = item['user_discord'] if 'user_discord' in item else None
            # this default username is tough but we'd have to work w/ it
            username = item['user'] if 'user' in item else deck_id.split('/')[-1].replace('.txt', '')[:-1]
            user_id = _create_user(client, shorten_name(username), discord)

            d = Deck()
            d.date = date_object
            # if comp_type == CompetitionType.GP:
            # d.deck_id = f'{comp.comp_id}--{clean_name(username)}'
            # else:
            d.deck_id = clean_name(deck_id[1:].replace('.txt', ''))
            d.format = 'msem'
            d.name = deckname
            if 'name' not in item:
                d.is_name_placeholder = True
            d.author = user_id
            d.competition = comp.competition_id
            d.mainboard = {smart_clean(name, all_cards): value['mainCount'] for name, value in cards.items() if
                           value['mainCount'] > 0}
            d.sideboard = {smart_clean(name, all_cards): value['sideCount'] for name, value in cards.items() if
                           value['sideCount'] > 0}
            d.is_sorted = False
            decks_by_id[d.deck_id] = d
        logger.info('Finished building decks')

        for deck_id, d in decks_by_id.items():
            _build_deck_record(d, matches, deck_id)
        logger.info('Finished building records')

        client.decks.insert_many([x.save() for x in decks_by_id.values()])
        logger.info('Operation complete.')

    except (DreadriseError, KeyError, ValueError):
        logger.error('A error occured!')
        traceback.print_exc()
