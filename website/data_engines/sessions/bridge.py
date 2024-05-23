from typing import Any, Callable, Mapping

from werkzeug import Response

from shared.helpers import configuration

from .firestore import get_session_firestore, save_session_firestore
from .flask import get_session_flask, save_session_flask


def get_session() -> tuple[Mapping[str, Any], Callable[[Response], None] | None]:
    session_functions = {
        'flask': get_session_flask,
        'firestore': get_session_firestore
    }
    return session_functions[configuration.get('session_backend')]()


def save_session(sess: dict[str, Any]) -> None:
    session_functions = {
        'flask': save_session_flask,
        'firestore': save_session_firestore
    }
    session_functions[configuration.get('session_backend')](sess)
