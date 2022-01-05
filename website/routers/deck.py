import datetime
import json
from typing import Any, Dict, Optional, cast

from flask import Blueprint, abort, flash, g, make_response, redirect, render_template, request
from plotly import utils
from pymongo.database import Database
from werkzeug import Response

from shared.helpers.db_loader import generate_popular_cards, load_deck_data, load_multiple_decks
from shared.helpers.deckcheck.core import deck_check
from shared.helpers.deckcheck.karsten import karsten_dict
from shared.helpers.metagame import metagame_breakdown
from shared.helpers.query import deck_privacy
from shared.helpers.util2 import build_deck
from shared.type_defaults import bye_user, get_blank_user
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.user import User
from website.util import get_dist, get_uid, has_priv, split_database, split_import, try_catch_json

b_deck = Blueprint('deck', __name__)


@b_deck.route('/<deck_id>')
@split_database
def single_deck(db: Database, deck_id: str) -> str:
    query = deck_privacy({'deck_id': deck_id}, get_uid(), True, is_admin=has_priv('deck_admin'))
    deck = db.decks.find_one(query)
    if not deck:
        flash(f'Deck with ID {deck_id} not found.')
        abort(404)

    loaded_deck = Deck().load(deck)
    dist = get_dist()
    if loaded_deck.competition:
        comp = db.competitions.find_one({'competition_id': loaded_deck.competition})
        if not comp:
            abort(404)
        competition: Optional[Competition] = Competition().load(comp)
        opposing_deck_ids = [x.opposing_deck_id for x in loaded_deck.games]
        opposing_decks = {x['deck_id']: Deck().load(x) for x in db.decks.find({'deck_id': {'$in': opposing_deck_ids}})}
        opponent_ids = [x.author for x in opposing_decks.values()]
        opponents = {x['user_id']: User().load(x) for x in db.users.find({'user_id': {'$in': opponent_ids}})}

        opponent_zip = []
        for i in loaded_deck.games:
            if not i.opposing_deck_id:
                opponent_zip.append((i, '-', '', get_blank_user('Bye')))
            else:
                xdeck = opposing_decks.get(i.opposing_deck_id)
                opponent_id = xdeck.author if xdeck else ''
                if not opponent_id or opponent_id not in opponents:
                    opponent_zip.append((i, 'Unknown', 'unknown', get_blank_user('Unknown')))
                else:
                    opp = opponents.get(opponent_id, bye_user)
                    # this is garbage but I'm too lazy to make a proper struct for this
                    opponent_zip.append((i, xdeck.name if xdeck else '-', xdeck.deck_id if xdeck else '', opp))
    else:
        competition = None
        opponent_zip = []
    return render_template('deck/single.html', data=load_deck_data(dist, loaded_deck),
                           comp=competition, opponents=opponent_zip)


@b_deck.route('/with/<card_id>')
@split_database
def decks_with_card(db: Database, card_id: str) -> str:
    card = db.cards.find_one({'card_id': card_id})
    if not card:
        flash(f'Card {card_id} not found')
        abort(404)

    loaded_card = Card().load(card)
    fmt = request.args.get('format')
    if not fmt:
        constants = split_import()
        fmt = constants.default_format
        if loaded_card.legality[fmt] not in ['legal', 'restricted']:
            for i in reversed(constants.scraped_formats):
                if loaded_card.legality[i] in ['legal', 'restricted']:
                    fmt = i
                    break
    return render_template('deck/with-card.html', card=loaded_card, format=fmt)


@b_deck.route('/editor')
@b_deck.route('/editor/<deck_id>')
@split_database
def deck_editor(db: Database, deck_id: str = '') -> str:
    query = deck_privacy({'deck_id': deck_id}, get_uid(), True, is_admin=has_priv('deck_admin'))
    deck = db.decks.find_one(query)
    session = g.actual_session
    can_edit = deck and 'competition' not in deck and 'user' in session and deck['author'] == session['user']['user_id']
    force_copy = request.args.get('copy')
    return render_template('deck/editor.html', deck_id=deck_id, copy=force_copy or not can_edit)


@b_deck.route('/delete/<deck_id>')
@split_database
def delete_deck(db: Database, deck_id: str = '') -> Response:
    user_id = get_uid()
    query = deck_privacy({'deck_id': deck_id}, user_id, True, is_admin=has_priv('deck_admin'))
    deck = db.decks.find_one(query)
    session = g.actual_session
    if deck and 'competition' not in deck and 'user' in session and deck['author'] == session['user']['user_id']:
        db.decks.delete_one({'deck_id': deck_id})
    return redirect(f'/users/{user_id}')


b_deck_api = Blueprint('deck_api', __name__)


@b_deck_api.route('/with-card/<card_id>')
@split_database
def api_decks_with_card(db: Database, card_id: str) -> dict:
    card = db.cards.find_one({'card_id': card_id})
    if not card:
        return {'decks': [], 'popular_cards': []}

    card_name = card['name']
    base_query: Dict[str, Any] = {'$or': [{f'mainboard.{card_name}': {'$gte': 1}},
                                          {f'sideboard.{card_name}': {'$gte': 1}}]}

    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    if 'all' not in fmt:
        base_query = {'$and': [base_query, {'format': fmt}]}
    query = deck_privacy(base_query, get_uid(), True, is_admin=has_priv('deck_admin'))

    deck_count = db.decks.find(query).count()
    if deck_count > 250:
        min_wins = 5 if deck_count > 1000 else 4
        query = {'$and': [{'wins': {'$gte': min_wins}}, query]}
    else:
        min_wins = 0
    decks = [Deck().load(x) for x in db.decks.find(query, sort=[('date', -1)])]

    dist = get_dist()
    loaded_decks, cd = load_multiple_decks(dist, decks)
    popular_card_data = generate_popular_cards(dist, cd, loaded_decks, threshold=10)
    base: Dict[str, Any] = {'decks': [x.jsonify() for x in loaded_decks],
                            'popular_cards': [x.jsonify() for x in popular_card_data]}
    if min_wins:
        base['partial_load'] = True
    return base


@b_deck_api.route('/metagame-with-card/<card_id>')
@split_database
def api_card_metagame_breakdown(db: Database, card_id: str) -> Response:
    card = db.cards.find_one({'card_id': card_id})
    if not card:
        flash(f'Card with id {card_id} not found.')
        abort(404)

    card_name = card['name']
    base_query: Dict[str, Any] = {'$or': [{f'mainboard.{card_name}': {'$gte': 1}},
                                          {f'sideboard.{card_name}': {'$gte': 1}}]}

    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    if 'all' not in fmt:
        base_query = {'$and': [base_query, {'format': fmt}]}

    query = {'$and': [base_query, {'competition': {'$exists': 1}}]}

    deck_count = db.decks.find(query).count()
    if deck_count > 250:
        min_wins = 5 if deck_count > 1000 else 4
        query = {'$and': [{'wins': {'$gte': min_wins}}, query]}
    else:
        min_wins = 0
    decks = [Deck().load(x) for x in db.decks.find(query)]
    fig = metagame_breakdown(db, decks, min_wins == 0)

    resp = make_response(json.dumps(fig, cls=utils.PlotlyJSONEncoder))
    resp.headers['Content-Type'] = 'application/json'
    return resp


def load_from_dict(x: Dict[str, int]) -> str:
    return '\n'.join([f'{u}x {v}' for v, u in x.items()])


@b_deck_api.route('/deck-list-text/<deck_id>')
@split_database
def deck_list_text(db: Database, deck_id: str) -> dict:
    user_id = get_uid()
    query = deck_privacy({'deck_id': deck_id}, user_id, True, is_admin=has_priv('deck_admin'))
    deck = db.decks.find_one(query)
    if not deck:
        return {'name': '?', 'str': ''}

    user = db.users.find_one({'user_id': deck['author']})
    appendix = ' by ' + user['nickname'] if user and deck['author'] != user['user_id'] else ''
    return {
        'name': deck['name'] + appendix,
        'str': load_from_dict(deck['mainboard']) + '\n\nSideboard:\n' + load_from_dict(deck['sideboard']),
        'format': deck['format'],
        'format_str': split_import().format_localization.get(deck['format'], deck['format'])
    }


@b_deck_api.route('/check', methods=['POST'])
def check_deck() -> dict:
    constants = split_import()
    req = cast(Dict[str, Any], request.get_json())
    deck_list = req['deck_list']
    deck = build_deck(deck_list)
    deck.format = str(req['format'])
    status, errors, warnings, messages = deck_check(get_dist(), deck, constants.deck_checkers)
    return {
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'messages': messages
    }


@b_deck_api.route('/karsten', methods=['POST'])
def karsten() -> dict:
    req = cast(Dict[str, Any], request.get_json())
    deck_list = req['deck_list']
    deck = build_deck(deck_list)
    status, errors, warnings, messages = karsten_dict(get_dist(), deck)
    return {
        'status': status,
        'errors': errors,
        'warnings': warnings,
        'messages': messages
    }


@b_deck_api.route('/formats')
def formats() -> dict:
    stuff = split_import()
    localization = stuff.format_localization
    fmts = [(x, localization.get(x, x)) for x in stuff.new_deck_formats]
    return {'objects': fmts}


@b_deck_api.route('/create', methods=['POST'])
@try_catch_json
@split_database
def create_deck(db: Database) -> dict:
    session = g.actual_session
    if 'user' not in session:
        return {'success': False, 'error': 'You need to be logged in to save decks!'}

    req = cast(Dict[str, Any], request.get_json())
    deck_list = req['deck_list']
    deck_name = req['name']
    if not deck_name:
        return {'success': False, 'error': 'Cannot create a deck without a name!'}
    deck_id = req['id']
    priv = req['privacy']
    fmt = req['format']
    generated = build_deck(deck_list)

    query = deck_privacy({'deck_id': deck_id}, get_uid(), True, is_admin=has_priv('deck_admin'))
    deck_obj = db.decks.find_one(query)
    deck = Deck().load(deck_obj) if deck_obj else None
    if not deck:
        generated.deck_id = deck_id
        generated.name = deck_name
        generated.author = session['user']['user_id']
        generated.format = fmt
        generated.privacy = priv
        generated.date = datetime.datetime.now()
        db.decks.insert_one(generated.save())
        return {'success': True, 'deck_id': deck_id}

    can_edit = not deck.competition and 'user' in session and deck.author == session['user']['user_id']
    if not can_edit:
        return {'success': False, 'error': 'Cannot edit this deck!'}
    db.decks.update_one({'deck_id': deck_id},
                        {'$set': {
                            'name': deck_name,
                            'mainboard': generated.mainboard,
                            'sideboard': generated.sideboard,
                            'privacy': priv,
                            'format': fmt
                        }})
    return {'success': True, 'deck_id': deck_id}
