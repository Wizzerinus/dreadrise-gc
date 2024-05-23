from typing import Any

current_session_version = 3

default_session: dict[str, Any] = {
    'version': current_session_version,
    'user': None,
    'logins': {}
}
