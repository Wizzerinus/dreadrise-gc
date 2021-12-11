from arrow import now
from authlib.integrations.base_client import MismatchingStateError
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, abort, g, redirect, request, url_for
from pymongo.database import Database
from werkzeug import Response

from shared.helpers.configuration import get
from shared.types.user import User
from website.util import get_dist, split_database

b_auth = Blueprint('auth', __name__)

oauth = OAuth()
oauth.register('discord', access_token_url='https://discord.com/api/oauth2/token',
               grant_type='authorization_code', api_base_url='https://discord.com/api/',
               authorize_url='https://discord.com/api/oauth2/authorize', scope='identify',
               client_id=get('DISCORD_CLIENT_ID'), client_secret=get('DISCORD_CLIENT_SECRET'))


@b_auth.route('/login/discord')
def discord_login() -> Response:
    if g.actual_session['user']:
        return redirect(url_for('index.index'))
    redirect_uri = url_for('.discord_authorize', _external=True)
    return oauth.discord.authorize_redirect(redirect_uri)


class DiscordToken(dict):  # Authlib is bugged right now, so I shall save it
    def is_expired(self) -> bool:
        return self['expires_at'] <= now().timestamp()


@b_auth.route('/login/discord2')
@split_database
def discord_authorize(db: Database) -> Response:
    if g.actual_session['user']:
        return redirect(url_for('index.index'))

    try:
        session = g.actual_session
        current_dist = get_dist()
        token = oauth.discord.authorize_access_token()
        me = oauth.discord.get('users/@me', token=DiscordToken(token))
        data = me.json()
        uid = data['id']

        # either logging in or creating a user with id `discord.{data.id}` and name `data.username`
        user = db.users.find_one({'login': f'discord.{uid}'})
        if not user:
            user = {
                'login': f'discord.{uid}',
                'username': data['username'],
                'privileges': {}
            }
            db.users.insert_one(user)

        if 'logins' not in session:
            session['logins'] = {}
        session['logins'][current_dist] = User().load(user).serialize()
        session['user'] = session['logins'][current_dist]
        g.session_dirty = True
        return redirect(url_for('index.index'))
    except MismatchingStateError:
        abort(401)


@b_auth.route('/logout')
def logout() -> Response:
    current_dist = get_dist()
    session = g.actual_session
    if 'logins' in session and current_dist in session['logins']:
        session['logins'].pop(current_dist, None)
        session['user'] = None
        g.session_dirty = True

    return redirect(url_for('index.index'))


@b_auth.route('/reload')
@split_database
def reload_auth(db: Database) -> Response:
    current_dist = get_dist()
    session = g.actual_session
    if 'logins' not in session or 'user' not in session:
        return redirect(url_for('index.index'))
    user = db.users.find_one({'user_id': session['user']['user_id']})
    if not user:
        session['logins'].pop(current_dist, None)
        session['user'] = None
    else:
        session['logins'][current_dist] = User().load(user).serialize()
        session['user'] = session['logins'][current_dist]
    g.session_dirty = True

    return redirect(request.referrer or url_for('index.index'))
