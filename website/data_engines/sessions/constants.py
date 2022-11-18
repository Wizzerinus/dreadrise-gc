from typing import Any, Dict

current_session_version = 3

default_session: Dict[str, Any] = {
    'version': current_session_version,
    'user': None,
    'logins': {}
}
