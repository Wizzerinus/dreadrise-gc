import logging
import traceback
from functools import wraps
from typing import Any, Callable, List, Optional

from flask import abort, g, jsonify, make_response, request

from shared.core_enums import Distribution, default_distribution, distribution_rollback
from shared.helpers.database import connect
from shared.helpers.util2 import get_dist_constants
from shared.types.dist_constants import DistConstants

logger = logging.getLogger('dreadrise.website')


def get_dist() -> Distribution:
    """
    Get the currently used distribution. Updates the session record if it changed.
    :return: the distribution being used
    """

    for url_part, dist_name in distribution_rollback.items():
        if url_part in request.url_root:
            return dist_name

    return default_distribution


def split_database(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorate a function, passing the database of the current distribution as the 1st parameter.
    :param f: the function to decorate
    :return: the decorated function
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        database = connect(get_dist())
        return f(database, *args, **kwargs)

    return decorated


def split_import() -> DistConstants:
    """
    Import all constants from a specified distribution.
    :return: the loaded module
    """
    return get_dist_constants(get_dist())


def requires_module(k: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            constants = split_import()
            if k not in constants.EnabledModules:
                abort(404)
            return f(*args, **kwargs)
        return decorated

    return decorate


def privileges_required(privileges: List[str]) -> Callable[[Callable[..., Any]], Any]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            good = 'user' in g.actual_session and g.actual_session['user'] and \
                'privileges' in g.actual_session['user'] and g.actual_session['user']['privileges']
            if good:
                good = len([x for x in privileges if x not in g.actual_session['user']['privileges']]) == 0
            if good:
                return f(*args, **kwargs)
            abort(401)
        return decorated

    return decorator


def try_catch_json(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except TypeError as e:
            logger.error('Error detected! TypeError - %s', e)
            traceback.print_exc()
            abort(make_response(jsonify(error='The server ran into a TypeError.'), 500))
        except KeyError as e:
            logger.error('Error detected! KeyError - %s', e)
            traceback.print_exc()
            abort(make_response(jsonify(error='The server ran into a KeyError.'), 500))
        except IndexError as e:
            logger.error('Error detected! IndexError - %s', e)
            traceback.print_exc()
            abort(make_response(jsonify(error='The server ran into a IndexError.'), 500))

    return decorated


def get_uid() -> Optional[str]:
    return g.actual_session['user']['user_id'] if g.actual_session['user'] else None


def has_priv(priv: str) -> bool:
    session = g.actual_session
    return session['user'] and priv in session['user']['privileges'] and session['user']['privileges'][priv]
