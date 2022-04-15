from math import ceil
from typing import Any, Dict, List, cast

from flask import Blueprint, render_template, request
from pymongo.database import Database

from shared.helpers.exceptions import DreadriseError
from shared.search.syntax import format_func
from website.util import get_dist, split_database, split_import

b_card_search = Blueprint('card_search', __name__)
b_card_search_api = Blueprint('card_search_api', __name__)


@b_card_search.route('/')
def card_search() -> str:
    return render_template('card-search/search.html')


@b_card_search_api.route('/cards', methods=['POST'])
@split_database
def api_card_search(db: Database) -> Dict[str, Any]:
    req = cast(Dict[str, Any], request.get_json())
    query = cast(str, req['query'])
    current_page = cast(int, req['page'])
    page_size = cast(int, req['page_size'])
    dist = get_dist()
    try:
        constants = split_import()
        matches, sample, _ = constants.CardSearchSyntax().search(dist, db, query, page_size, current_page * page_size)
        return {
            'matches': matches,
            'sample': [x.virtual_save() for x in sample],
            'max_page': ceil(matches / page_size),
            'success': True
        }
    except DreadriseError as e:
        return {
            'success': False,
            'reason': str(e)
        }


@b_card_search_api.route('/card-defs', methods=['POST'])
@split_database
def api_card_defs(db: Database) -> Dict[str, Any]:
    req = cast(Dict[str, Any], request.get_json())
    card_list = cast(List[str], req['list'])
    field = cast(str, req['field'])
    if len(card_list) > 70:
        return {}
    return {x['name']: x[field] for x in db.cards.find({'name': {'$in': card_list}})}


@b_card_search_api.route('/syntax')
def api_card_search_syntax() -> Dict[str, List[str]]:
    constants = split_import()
    funcs_dict = constants.CardSearchSyntax().funcs
    funcs = [format_func(x, y) for x, y in funcs_dict.items()]
    funcs_str = sorted([x for x in funcs if x])
    at_sign = ['<code>@</code> sign can be prepended before the query to search card faces instead of the whole card. '
               'Example: ',
               '<code>@cmc:1 @cmc:2</code> finds all cards which have a face with mana value 1 and a face with mana '
               'value 2.',
               '<code>@</code> can be also used with groups, for example, <code>@(cmc:1 t:instant)</code> finds '
               'cards which have a 1-cmc instant side.',
               '<code>order</code> can accept either <code>[sort_type]</code> or <code>[sort_type]-[direction]</code>,'
               'where <code>[direction]</code> is <code>asc</code> or <code>desc</code> and',
               '<code>[sort_type]</code> is one of <code>mv, rarity, color</code>. The default sort method is ascending'
               ' by name.']
    scryfall = 'This search engine is heavily inspired by Scryfall and works similarly.'
    explanation = 'A query is a set of keywords (listed below). Keywords can be grouped with parens <code>()</code> ' \
                  'and with operators <code>or</code> and <code>and</code> (default).'
    categories = ['Some cards have categories that can be queried with the <code>is</code> or <code>not</code> '
                  'operators. All of them are listed below.'] + \
        [f'<code>{x}</code>: {y}' for x, y in constants.CategoryDescriptions]

    return {'keywords': funcs_str, 'start': [scryfall, explanation], 'extras': at_sign, 'categories': categories}
