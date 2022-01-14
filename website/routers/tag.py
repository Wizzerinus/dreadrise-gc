from math import ceil
from typing import Any, Dict

from flask import Blueprint, abort, flash, render_template, request
from pymongo.database import Database

from shared.helpers.db_loader import load_deck_analysis
from shared.helpers.query import deck_privacy
from shared.helpers.util import clean_name
from shared.helpers.util2 import get_dist_constants
from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag
from website.util import get_dist, get_uid, has_priv, split_database, split_import

b_tags = Blueprint('tags', __name__)


@b_tags.route('/<tag_id>')
@split_database
def single(db: Database, tag_id: str) -> str:
    tag = db.deck_tags.find_one({'tag_id': tag_id})
    if not tag:
        flash(f'Tag with ID {tag_id} not found.')
        abort(404)

    dist = get_dist()
    constants = get_dist_constants(dist)
    init_query = {'tags': tag_id}
    fmt = request.args.get('format', constants.default_format)
    if 'all' not in fmt:
        init_query['format'] = fmt

    query = deck_privacy(init_query, get_uid(), True, is_admin=has_priv('deck_admin'))
    decks = [Deck().load(x) for x in db.decks.find(query)]
    deck_analysis = load_deck_analysis(get_dist(), decks, threshold=0.05 if 'all' in fmt else 0.2)

    tag_cover = db.archetype_cache.find_one({'tag': tag_id, 'format': fmt})
    main_card = clean_name(tag_cover['cards'][0]) if tag_cover else constants.default_card
    return render_template('tag/single.html', tag=DeckTag().load(tag), analysis=deck_analysis,
                           bg_card=main_card, format=fmt)


@b_tags.route('/')
def all_tags() -> str:
    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    return render_template('tag/all.html', format=fmt)


b_tags_api = Blueprint('tags_api', __name__)


@b_tags_api.route('/all')
@b_tags_api.route('/all/<int:page>')
@split_database
def api_archetypes(db: Database, page: int = 1) -> dict:
    constants = split_import()
    fmt = request.args.get('format', constants.default_format)
    q: Dict[str, Any] = {'cards.0': {'$exists': True}}
    if 'all' not in fmt:
        q['format'] = fmt
    tcount = db.archetype_cache.find(q).count()
    # I have no idea why mongotypes doesn't support cursor slicing
    tags = list(db.archetype_cache.find(  # type: ignore
        q, sort=[('deck_count', -1), ('deck_winrate', -1), ('tag_name', 1)])
        [page * 60 - 60:page * 60])
    card_request = [x for y in tags for x in y['cards']]
    cards = {x['name']: Card().load(x) for x in db.cards.find({'name': {'$in': card_request}})}
    for i in tags:
        del i['_id']
        i['f_cards'] = [{'name': cards[i].singular_name, 'card_id': cards[i].card_id} for i in i['cards']]
    return {
        'success': True,
        'matches': tcount,
        'sample': tags,
        'page_size': 60,
        'page_num': page,
        'last_page': ceil(tcount / 60)
    }
