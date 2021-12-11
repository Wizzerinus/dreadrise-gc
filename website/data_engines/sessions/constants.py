from typing import Any, Dict

from shared.core_enums import default_distribution

current_session_version = 2

default_session: Dict[str, Any] = {
    'version': current_session_version,
    'user': None,
    'dist': default_distribution,
    'logins': {}
}
