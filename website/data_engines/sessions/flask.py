from typing import Any, Callable, Mapping, Optional, Tuple

from flask import session
from werkzeug import Response

from website.data_engines.sessions.constants import current_session_version, default_session


def get_session_flask() -> Tuple[Mapping[str, Any], Optional[Callable[[Response], None]]]:
    if 'version' not in session or session['version'] != current_session_version:
        for i, j in default_session.items():
            session[i] = j
        session.permanent = True
    return session, None


def save_session_flask(data: Mapping[str, Any]) -> None:
    session.modified = True
