import logging

from flask import Blueprint, redirect, render_template, request
from pymongo.database import Database
from werkzeug import Response

from shared.core_enums import distribution_rollback
from shared.helpers.db_loader import load_competitions
from shared.types.caching import FormatPopularity
from website.util import get_dist, split_database, split_import, swap_logins

b_index = Blueprint('index', __name__)
logger = logging.getLogger('dreadrise.website.index')


@b_index.route('/')
@b_index.route('/index')
def index() -> str:
    logger.debug('Start /index')
    constants = split_import()
    loaded = load_competitions(get_dist(), {'type': {'$in': constants.index_types}})
    logger.debug('Loaded competitions')
    loaded.sort(key=lambda x: x.competition.date, reverse=True)

    return render_template('index/index.html', comps=loaded[:3])


@b_index.route('/formats')
@split_database
def formats(db: Database) -> str:
    logger.debug('Start /formats')
    fmts = {x['format']: FormatPopularity().load(x) for x in db.format_popularities.find({})}
    logger.debug('Loaded formats')

    constants = split_import()
    fmts_ordered = []
    for i in reversed(constants.formats):
        if i in fmts:
            fmts_ordered.append((i, constants.format_localization[i], fmts[i]))
    logger.debug('Sorted formats')

    redirect_to = request.args.get('redirect_to', 'competitions').replace('.', '/')
    only_when_legal = request.args.get('only_when_legal', '')
    if only_when_legal:
        da_card = db.cards.find_one({'card_id': only_when_legal})
        if da_card:
            fmts_ordered = [x for x in fmts_ordered if da_card['legality'][x[0]] in ['legal', 'restricted']]

    if len(fmts_ordered) > 1:
        dfp = FormatPopularity()
        dfp.format = '_all'
        dfp.card_name = constants.default_card
        dfp.deck_count = sum([x[2].deck_count for x in fmts_ordered])
        fmts_ordered.insert(1, ('_all', 'All formats', dfp))
    return render_template('index/formats.html', formats=fmts_ordered, redirect_to=redirect_to)


@b_index.route('/dist-change/<dist>')
def dist_change(dist: str) -> Response:
    if dist in distribution_rollback:
        swap_logins(distribution_rollback[dist])

    ref_split = request.referrer.split('?')
    if len(ref_split) != 2:
        return redirect(request.referrer)

    full_split = ref_split[1].split('&')
    full_split = [x for x in full_split if 'dist' not in x]
    start_url = ref_split[0] + '?' + '&'.join(full_split)
    return redirect(start_url)
