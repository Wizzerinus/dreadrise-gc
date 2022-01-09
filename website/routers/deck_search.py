from math import ceil
from pprint import pprint
from typing import Any, Dict, List, cast

import arrow
from flask import Blueprint, render_template, request
from pymongo.database import Database

from shared.helpers.db_loader import load_multiple_decks
from shared.helpers.exceptions import DreadriseError
from shared.search.syntax import format_func
from website.util import get_dist, split_database, split_import

b_deck_search = Blueprint('deck_search', __name__)
b_deck_search_api = Blueprint('deck_search_api', __name__)


@b_deck_search.route('/')
def deck_search() -> str:
    return render_template('deck-search/search.html')


@b_deck_search.route('/matchups')
def matchup_search() -> str:
    return render_template('deck-search/matchups.html')


@b_deck_search_api.route('/decks', methods=['POST'])
@split_database
def api_card_search(db: Database) -> Dict[str, Any]:
    req = cast(Dict[str, Any], request.get_json())
    query = cast(str, req['query'])
    current_page = cast(int, req['page'])
    page_size = cast(int, req['page_size'])
    try:
        constants = split_import()
        matches, sample, extras = constants.deck_search_syntax().search(db, query, page_size, current_page * page_size)
        sample_arr = [x.jsonify() for x in load_multiple_decks(get_dist(), sample)[0]]
        for item, item_og in zip(sample_arr, sample):
            try:
                del item['card_defs']
                del item['deck']['mainboard_list']
                del item['deck']['sideboard_list']
                del item['deck']['date']
                del item['deck']['privacy']
            except KeyError:
                pass
            item['friendly_date'] = arrow.get(item_og.date).humanize()

        if extras['winrate']:
            winrate = round(100 * extras['winrate'][0]['wins'] /
                            max(1, extras['winrate'][0]['wins'] + extras['winrate'][0]['losses']), 2)
        else:
            winrate = 0

        return {
            'matches': matches,
            'sample': sample_arr,
            'winrate': winrate,
            'max_page': ceil(matches / page_size),
            'success': True
        }
    except DreadriseError as e:
        return {
            'success': False,
            'reason': str(e)
        }


@b_deck_search_api.route('/matchups', methods=['POST'])
@split_database
def api_matchup_search(db: Database) -> Dict[str, Any]:
    req = cast(Dict[str, Any], request.get_json())
    q1 = cast(str, req['q1'])
    q2 = cast(str, req['q2'])
    current_page = cast(int, req['page'])
    page_size = cast(int, req['page_size'])
    try:
        constants = split_import()
        dss = constants.deck_search_syntax()
        hero, ef_hero, dd_hero = dss.create_pipeline(q1, page_size, current_page * page_size)
        intermediate = [
            {'$unwind': '$games'},
            {'$lookup': {'from': 'decks', 'localField': 'games.opposing_deck_id',
                         'foreignField': 'deck_id', 'as': 'enemy'}},
            {'$unwind': '$enemy'}
        ]
        enemy, ef_enemy, dd_enemy = dss.create_pipeline(q2, page_size, current_page * page_size)
        enemy = dss.arc.rename_pipeline(enemy, lambda x: f'enemy.{x}')
        hero_fixed, hero_f = dss.remove_facets(hero)
        enemy_fixed, enemy_f = dss.remove_facets(enemy)
        winrate_facet = [
            {'$project': {
                '_id': 0,
                'player_wins': {'$cond': [{'$gte': ['$games.player_wins', 2]}, 1, 0]},
                'player_losses': {'$cond': [{'$gte': ['$games.player_losses', 2]}, 1, 0]},
            }},
            {'$group': {'_id': None, 'wins': {'$sum': '$player_wins'}, 'losses': {'$sum': '$player_losses'}}}
        ]
        sample_additions = [
            {'$project': {
                '_id': 0,
                'deck_id': 1, 'name': 1, 'author': 1, 'date': 1,
                'enemy_deck_id': '$enemy.deck_id', 'enemy_name': '$enemy.name', 'enemy_author': '$enemy.author',
                'game_wins': '$games.player_wins', 'game_losses': '$games.player_losses', 'winner': '$games.result'
            }}
        ]
        enemy_f[0]['$facet']['winrate'] = winrate_facet
        enemy_f[0]['$facet']['sample'] = sample_additions + enemy_f[0]['$facet']['sample']
        d = (dd_hero, dd_enemy)
        ef = ['winrate']

        matches, sample, extras = dss.search_with_pipeline(db, hero_fixed + intermediate + enemy_fixed + enemy_f, ef, d)
        if extras['winrate']:
            winrate = round(100 * extras['winrate'][0]['wins'] /
                            max(1, extras['winrate'][0]['wins'] + extras['winrate'][0]['losses']), 2)
        else:
            winrate = 0

        user_id_list = [x.author for x in sample] + [x.enemy_author for x in sample]
        users = {x['user_id']: x['nickname'] for x in db.users.find({'user_id': {'$in': user_id_list}})}
        for x in sample:
            x.author_name = users[x.author]
            x.enemy_author_name = users[x.enemy_author]

        return {
            'matches': matches,
            'sample': [x.virtual_save() for x in sample],
            'winrate': winrate,
            'max_page': ceil(matches / page_size),
            'success': True
        }
    except DreadriseError as e:
        return {
            'success': False,
            'reason': str(e)
        }


@b_deck_search_api.route('/syntax')
def api_deck_search_syntax() -> Dict[str, List[str]]:
    constants = split_import()
    funcs_dict = constants.deck_search_syntax().funcs
    funcs = [format_func(x, y) for x, y in funcs_dict.items()]
    funcs_str = sorted([x for x in funcs if x])
    at_sign = ['To use <code>card</code> and <code>side</code> keywords with specific card numbers, put them '
               'after a dot, like this: <code>card.4="delver of secrets"</code>',
               'The number defaults to 1. Fuzzy card search is allowed and returns all matching cards.']
    scryfall = 'This search engine is heavily inspired by Scryfall and works similarly.'
    explanation = 'A query is a set of keywords (listed below). Keywords can be grouped with parens <code>()</code> ' \
                  'and with operators <code>or</code> and <code>and</code> (default).'

    return {'keywords': funcs_str, 'start': [scryfall, explanation], 'extras': at_sign}
