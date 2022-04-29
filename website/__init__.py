import logging
from typing import Any, Callable, Dict, List, Tuple, cast

import yaml
from flask import Flask, Response, g, render_template, request
from jinja2 import Markup

from shared.core_enums import Distribution, distribution_localization, distributions
from shared.helpers import configuration
from shared.helpers.configuration import cache
from shared.helpers.database import connect
from shared.helpers.logging import initlogger
from shared.helpers.magic import process_mana_cost_text, process_oracle
from shared.helpers.util import clean_name, get_legality_color, shorten_name
from shared.helpers.util2 import update_distributions
from website.data_engines.sessions.bridge import get_session, save_session
from website.routers.admin import b_admin, b_admin_api
from website.routers.auth import b_auth, oauth
from website.routers.card import b_card
from website.routers.card_search import b_card_search, b_card_search_api
from website.routers.competition import b_competition, b_competition_api
from website.routers.deck import b_deck, b_deck_api
from website.routers.deck_search import b_deck_search, b_deck_search_api
from website.routers.gateway import b_gateway
from website.routers.imagery import b_imagery
from website.routers.index import b_index
from website.routers.tag import b_tags, b_tags_api
from website.routers.tools import b_tools, b_tools_api
from website.routers.user import b_user, b_user_api
from website.util import get_dist, split_import

logger = logging.getLogger('dreadrise.website')

app = Flask(__name__)
app.config.from_file('../config/core.yml', lambda f: yaml.load(f, Loader=yaml.SafeLoader))
app.secret_key = configuration.get('secret_key')

app.jinja_env.filters['oraclize'] = process_oracle
app.jinja_env.filters['mana'] = process_mana_cost_text
app.jinja_env.filters['clean'] = clean_name
app.jinja_env.filters['shorten'] = shorten_name

app.register_blueprint(b_index)
app.register_blueprint(b_card_search, url_prefix='/card-search')
app.register_blueprint(b_card_search_api, url_prefix='/api/card-search')
app.register_blueprint(b_deck_search, url_prefix='/deck-search')
app.register_blueprint(b_deck_search_api, url_prefix='/api/deck-search')
app.register_blueprint(b_card, url_prefix='/cards')
app.register_blueprint(b_deck, url_prefix='/decks')
app.register_blueprint(b_deck_api, url_prefix='/api/decks')
app.register_blueprint(b_user, url_prefix='/users')
app.register_blueprint(b_user_api, url_prefix='/api/users')
app.register_blueprint(b_auth, url_prefix='/auth')
app.register_blueprint(b_admin, url_prefix='/admin')
app.register_blueprint(b_admin_api, url_prefix='/api/admin')
app.register_blueprint(b_competition, url_prefix='/competitions')
app.register_blueprint(b_competition_api, url_prefix='/api/competitions')
app.register_blueprint(b_tags, url_prefix='/tags')
app.register_blueprint(b_tags_api, url_prefix='/api/tags')
app.register_blueprint(b_tools, url_prefix='/tools')
app.register_blueprint(b_tools_api, url_prefix='/api/tools')

app.register_blueprint(b_imagery, url_prefix='/imagery')
app.register_blueprint(b_gateway, url_prefix='/api/gateway')


def find_random_card(dist: Distribution, txt: str, default: str) -> Tuple[str, str]:
    db = connect(dist)
    pipeline: List[Dict[str, Any]] = [{'$match': {'card_id': {'$regex': txt}}},
                                      {'$project': {'name': 1, 'card_id': 1}}, {'$sample': {"size": 1}}]

    for aggregated in db.cards.aggregate(pipeline):
        return aggregated['name'], aggregated['card_id']
    return default, default.lower()


@app.errorhandler(404)  # type: ignore
def page_not_found(*args: Any):  # type: ignore
    if '/api/' in request.full_path:
        return {'success': False, 'reason': f'Page not found: {request.full_path}'}, 403
    markup = Markup(f'<code>{request.full_path}</code>')
    return render_template('error.html', error=404, card=find_random_card(get_dist(), 'lost', 'island'),
                           error_msg=f'Page {markup} not found.'), 404


@app.errorhandler(401)  # type: ignore
def page_forbidden(*args: Any):  # type: ignore
    if '/api/' in request.full_path:
        return {'success': False, 'reason': f'Access denied: {request.full_path}'}, 401
    return render_template('error.html', error=401, card=find_random_card(get_dist(), 'forbid', 'swamp'),
                           error_msg='You don\'t have access to this page.'), 401


@app.errorhandler(500)  # type: ignore
def page_error(*args: Any):  # type: ignore
    logger.error('500 error! %s', args)
    if '/api/' in request.full_path:
        return {'success': False, 'reason': 'Internal server error!'}, 500
    return render_template('error.html', error=500, card=find_random_card(get_dist(), 'chaos', 'mountain'),
                           error_msg='The server errored. Notify the Dreadrise developer about this.'), 500


@app.context_processor
def inject_configuration() -> Dict[str, Any]:
    cdist = get_dist()
    stuff = split_import()
    formats = stuff.Formats
    localization = stuff.FormatLocalization

    def split_legality(ld: Dict) -> List[Tuple[str, str, str]]:
        return [(localization[x], ld[x].replace('_', ' '), get_legality_color(ld[x])) for x in formats if x in ld]

    return {
        'config': cache.get(cdist, cache['default']),
        'distributions': distribution_localization,
        'formats': dict(localization, _all='All formats'),
        'cdist': cdist,
        'split_legality': split_legality,
        'scraped_formats': stuff.ScrapedFormats,
        'default_format': stuff.DefaultFormat
    }


@app.before_request
def before_request() -> None:
    g.actual_session, g.update_session = get_session()
    g.session_dirty = False


@app.after_request
def after_request(r: Response) -> Response:
    if g.session_dirty:
        save_session(g.actual_session)
        g.session_dirty = False
    elif g.update_session:
        cast(Callable[[Response], None], g.update_session)(r)
    return r


oauth.init_app(app)


def run(debug: bool = False) -> None:
    for i in distributions:
        if i != 'default':
            logger.info(f'Connecting to {i}')
            connect(i)
    logger.info('Running app')
    app.run(host='0.0.0.0', port=configuration.get_int('PORT'), debug=debug)


def gunicorn() -> Flask:
    initlogger()
    update_distributions()
    for i in distributions:
        if i != 'default':
            logger.info(f'Connecting to {i}')
            connect(i)
            logger.info('Connected')
    return app
