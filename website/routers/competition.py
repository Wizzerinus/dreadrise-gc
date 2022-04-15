import json
from math import ceil
from typing import Any, Dict

from flask import Blueprint, abort, flash, make_response, render_template, request
from plotly import utils
from pymongo.database import Database
from werkzeug import Response

from shared.helpers.db_loader import load_competition_single, load_competitions
from shared.helpers.metagame import metagame_breakdown
from shared.types.competition import Competition
from shared.types.deck import Deck
from website.util import get_dist, split_database, split_import

b_competition = Blueprint('competition', __name__)


@b_competition.route('/<competition_id>')
def single_competition(competition_id: str) -> str:
    dist = get_dist()
    competitions = load_competitions(dist, {'competition_id': competition_id})
    if not competitions:
        flash(f'Competition {competition_id} not found')
        abort(404)
    return render_template('competition/single.html', data=competitions[0])


@b_competition.route('/')
def all_competitions() -> str:
    constants = split_import()
    fmt = request.args.get('format', constants.DefaultFormat)
    return render_template('competition/all.html', format=fmt)


b_competition_api = Blueprint('competition_api', __name__)


@b_competition_api.route('/all')
@b_competition_api.route('/all/<int:page>')
@split_database
def api_competitions(db: Database, page: int = 0) -> dict:
    constants = split_import()
    fmt = request.args.get('format', constants.DefaultFormat)
    query = {} if 'all' in fmt else {'format': fmt}
    ccount = db.competitions.find(query).count()
    competition_cursor = db.competitions.find(query, sort=[('date', -1)])[page * 12 - 12:page * 12]  # type: ignore
    comps = [Competition().load(x) for x in competition_cursor]
    dist = get_dist()
    loaded_comps = [load_competition_single(dist, x, set()).jsonify() for x in comps]
    return {
        'success': True,
        'matches': ccount,
        'sample': loaded_comps,
        'page_size': 12,
        'page_num': page,
        'last_page': ceil(ccount / 12)
    }


@b_competition_api.route('/single/<competition_id>')
def api_single_competition(competition_id: str) -> dict:
    dist = get_dist()
    competitions = load_competitions(dist, {'competition_id': competition_id}, {'users', 'tags', 'cards', 'decks'})
    if not competitions:
        return {}
    return competitions[0].jsonify()


@b_competition_api.route('/metagame/<competition_id>')
@split_database
def api_metagame_breakdown(db: Database, competition_id: str) -> Response:
    # competition = Competition.objects(comp_id=name).first()
    competition_obj = db.competitions.find_one({'competition_id': competition_id})
    if not competition_obj:
        flash(f'Competition with ID {competition_id} not found.')
        abort(404)

    # decks = list(Deck.objects(competition=competition))
    query: Dict[str, Any] = {'competition': competition_id}
    deck_count = db.decks.find(query).count()
    if deck_count > 500:
        min_wins = 5 if deck_count > 2000 else 4
        query['wins'] = {'$gte': min_wins}
    else:
        min_wins = 0
    decks = [Deck().load(x) for x in db.decks.find(query)]
    fig = metagame_breakdown(db, decks, min_wins == 0)

    resp = make_response(json.dumps(fig, cls=utils.PlotlyJSONEncoder))
    resp.headers['Content-Type'] = 'application/json'
    return resp
