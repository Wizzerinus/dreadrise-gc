import logging
import traceback
from time import sleep
from typing import Dict, Optional

import arrow
from pymongo.database import Database

from shared import fetch_tools
from shared.helpers.database import connect
from shared.helpers.exceptions import DreadriseError, RisingDataError
from shared.helpers.util import clean_card, clean_name, fix_long_words, shorten_name
from shared.helpers.util2 import calculate_color_data
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


def get_match(x: dict, position: int, legacy: Dict[str, str] = None) -> DeckGameRecord:
    dg = DeckGameRecord()
    try:
        opposing_uid = legacy[x['players'][1 - position]['username']] if legacy else x['players'][1 - position]['list']
        dg.opposing_deck_id = opposing_uid if opposing_uid and 'bye' not in opposing_uid.lower() else None
    except KeyError:
        # bye
        pass
    dg.player_wins = int(x['players'][position]['wins'])
    dg.player_losses = int(x['players'][position]['losses'])
    # dg.winner = bool(x['players'][position]['victor' if 'victor' in x['players'][position] else 'winner'])
    dg.result = 0 if dg.player_losses == dg.player_wins else (1 if dg.player_wins > dg.player_losses else -1)
    return dg


def _build_deck_record(deck: Deck, matches: list, uid: str, legacy: Dict[str, str] = None) -> None:
    key = 'list' if not legacy else 'username'
    first_matches = [(k, get_match(x, 0, legacy)) for k, x in enumerate(matches) if key in x['players'][0] and
                     x['players'][0][key] == uid]
    second_matches = [(k, get_match(x, 1, legacy)) for k, x in enumerate(matches) if key in x['players'][1] and
                      x['players'][1][key] == uid]
    all_games = first_matches + second_matches
    deck.games = [x[1] for x in sorted(all_games)]
    deck.wins = len([x for x in all_games if x[1].result == 1])
    deck.losses = len([x for x in all_games if x[1].result == -1])
    deck.ties = len([x for x in all_games if x[1].result == 0])


def smart_clean(name: str, cards: Dict[str, Card]) -> str:
    name = clean_card(name).split(' // ')[0].split(' (')[0]
    if name not in cards:
        # logger.error(f'Card {name} not found')
        return name
    return cards[name].name


def run_json(json: dict, timeout: bool = True, card_cache: Optional[Dict[str, Card]] = None) -> Dict[str, Card]:
    logger.info('Connecting to the database')
    client = connect('msem')

    already_loaded_cards = {} if not card_cache else set(card_cache.keys())
    logger.info('Loading cards')
    if card_cache:
        all_cards = card_cache
    else:
        init_cards = {x['name']: Card().load(x) for x in client.cards.find({'layout': {'$ne': 'normal'}})}
        all_cards = card_cache or {}
        for k, v in init_cards.items():
            all_cards[k] = v
            if len(v.faces) > 1:
                for f in v.faces:
                    all_cards[f.name] = v
                all_cards[' // '.join([x.name for x in v.faces])] = v

    all_card_set = {clean_card(x) for y in json['decks'] for x in y['cards'] if x not in already_loaded_cards}
    non_split_names = [x for x in all_card_set if x not in all_cards]
    non_split_iter = ((x['name'], Card().load(x)) for x in client.cards.find({'name': {'$in': non_split_names}}))
    for name, card in non_split_iter:
        all_cards[name] = card
    logger.info('{n} decks, {m} matches, {k} cards loaded'.format(n=len(json['decks']), m=len(json['matches']),
                                                                  k=len(all_cards)))

    comp_name, date, decks, matches = json['competition_name'], json['date'], json['decks'], json['matches']
    date_object = arrow.get('20' + date.replace('_', '-')).datetime

    old_comp = client.competitions.find_one({'name': comp_name})
    # comp = Competition.objects(name=comp_name).first()
    if old_comp:
        if timeout:
            logger.warning(f'Deleting {comp_name} in 5 seconds!')
            sleep(5)
        client.competitions.delete_one({'name': comp_name})
        client.decks.delete_many({'competition': clean_name(comp_name)})
        logger.warning(f'Deleted {comp_name}.')

    if not decks:
        logger.info('Not inserting any decks.')
        return all_cards

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
    decks_by_name = {}
    legacy_deck_ids = {}
    for item in decks:
        cards, deck_id = item['cards'], item.get('deck_id', '')
        if 'name' in item:
            deckname = item['name']
        elif 'deck_name' in item:
            deckname = item['deck_name']
        else:
            deckname = 'No name'
        discord = item['user_discord'] if 'user_discord' in item else None
        # this default username is tough but we'd have to work w/ it
        if not deck_id and 'user' not in item:
            raise RisingDataError('Some deck is missing both User and Deck ID keys!')
        username = item['user'] if 'user' in item else deck_id.split('/')[-1].replace('.txt', '')[:-1]
        removal = f"{username}'s "
        deckname = fix_long_words(deckname.replace(removal, ''))
        user_id = _create_user(client, shorten_name(username), discord)

        d = Deck()
        d.date = date_object
        # if comp_type == CompetitionType.GP:
        # d.deck_id = f'{comp.comp_id}--{clean_name(username)}'
        # else:
        if deck_id:
            d.deck_id = clean_name(deck_id[1:].replace('.txt', ''))
            decks_by_id[d.deck_id] = d
        else:
            d.deck_id = comp.competition_id + '-' + clean_name(username)
            decks_by_name[username] = d
            legacy_deck_ids[username] = d.deck_id
        d.format = 'msem'
        d.name = deckname
        if 'name' not in item and 'deck_name' not in item:
            d.is_name_placeholder = True
        d.author = user_id
        d.competition = comp.competition_id
        d.mainboard = {smart_clean(name, all_cards): value['mainCount'] for name, value in cards.items() if
                       value['mainCount'] > 0}
        d.sideboard = {smart_clean(name, all_cards): value['sideCount'] for name, value in cards.items() if
                       value['sideCount'] > 0}
        d.is_sorted = False
        d.color_data = calculate_color_data(d, all_cards)
    logger.info('Finished building decks')

    if decks_by_name:
        logger.warning(f'Using obsolete data format for {comp_name}!')
        for deck_name, d in decks_by_name.items():
            _build_deck_record(d, matches, deck_name, legacy_deck_ids)
    for deck_id, d in decks_by_id.items():
        _build_deck_record(d, matches, deck_id, None)
    logger.info('Finished building records')

    client.decks.insert_many([x.save() for x in decks_by_id.values()] + [x.save() for x in decks_by_name.values()])
    logger.info('Operation complete.')
    return all_cards


def run() -> None:
    """
    Download a MSEM competition from the server and saves them into the database.
    :return: nothing
    """

    logger.info('Loading MSEM decks')
    json = fetch_tools.fetch_json(_competition_file_path)

    try:
        run_json(json)
    except (DreadriseError, KeyError, ValueError):
        logger.error('A error occured!')
        traceback.print_exc()
