import json

from flask import Blueprint, Response, abort, flash, make_response, render_template, request
from plotly import utils
from pymongo.database import Database

from shared.helpers.db_loader import generate_popular_cards, load_multiple_decks
from shared.helpers.metagame import metagame_breakdown
from shared.helpers.query import deck_privacy
from shared.types.deck import Deck
from shared.types.user import User
from website.util import get_dist, get_uid, has_priv, split_database, split_import

b_user = Blueprint('user', __name__)
b_user_api = Blueprint('user_api', __name__)


@b_user.route('/<user_id>')
@split_database
def user_page(db: Database, user_id: str) -> str:
    user = db.users.find_one({'user_id': user_id})
    if not user:
        flash(f'User {user_id} not found')
        abort(404)

    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    return render_template('user/single.html', user=User().load(user), format=fmt)


@b_user_api.route('/decks/<user_id>')
@split_database
def api_decks_by_user(db: Database, user_id: str) -> dict:
    user = db.users.find_one({'user_id': user_id})
    if not user:
        return {'decks': [], 'popular_cards': []}

    query = {'author': user_id}
    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    if 'all' not in fmt:
        query['format'] = fmt
    query = deck_privacy(query, get_uid(), True, is_admin=has_priv('deck_admin'))
    decks = [Deck().load(x) for x in db.decks.find(query, sort=[('date', -1)])]

    dist = get_dist()
    loaded_decks, cd = load_multiple_decks(dist, decks)
    popular_card_data = generate_popular_cards(dist, cd, loaded_decks, threshold=10)
    base = {'decks': [x.jsonify() for x in loaded_decks], 'popular_cards': [x.jsonify() for x in popular_card_data]}
    return base


@b_user_api.route('/metagame-user/<user_id>')
@split_database
def api_user_metagame_breakdown(db: Database, user_id: str) -> Response:
    user = db.users.find_one({'user_id': user_id})
    if not user:
        flash(f'User with id {user_id} not found.')
        abort(404)

    query = {'author': user_id, 'competition': {'$exists': 1}}
    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    if 'all' not in fmt:
        query['format'] = fmt

    decks = [Deck().load(x) for x in db.decks.find(query)]
    fig = metagame_breakdown(db, decks)

    resp = make_response(json.dumps(fig, cls=utils.PlotlyJSONEncoder))
    resp.headers['Content-Type'] = 'application/json'
    return resp
