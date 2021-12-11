from copy import deepcopy
from typing import Any, Callable, Dict, Mapping, Optional, Tuple
from uuid import uuid4

import arrow
from flask import request
from werkzeug import Response

from website.data_engines.sessions.constants import current_session_version, default_session

connection: Dict[str, Any] = {'db': None, 'sessions': None}


def initialize() -> None:
    from google.cloud import firestore

    connection['db'] = firestore.Client()
    connection['sessions'] = connection['db'].collection('sessions')


def get_session_firestore() -> Tuple[Mapping[str, Any], Optional[Callable[[Response], None]]]:
    session_cookie = request.cookies.get('fs_session_id')
    cookie_needs_updating = False
    if not session_cookie:
        session_cookie = str(uuid4())
        cookie_needs_updating = True

    db, sessions = connection['db'], connection['sessions']
    if not db:
        raise ConnectionError('Not connected to Firestore')
    doc_ref = sessions.document(document_id=session_cookie)
    transaction = db.transaction()
    doc = doc_ref.get(transaction=transaction)
    if doc.exists:
        if current_session_version == doc.get('version'):
            return doc.to_dict(), None
        cookie_needs_updating = True

    session = deepcopy(default_session)
    transaction.set(doc_ref, session)

    def update_response(r: Response) -> None:
        if session_cookie:
            r.set_cookie('fs_session_id', session_cookie, expires=arrow.now().shift(days=30).datetime)

    return session, update_response if cookie_needs_updating else None


def save_session_firestore(data: Dict[str, Any]) -> None:
    db, sessions = connection['db'], connection['sessions']
    if not db:
        raise ConnectionError('Not connected to Firestore')

    session_cookie = request.cookies.get('fs_session_id')
    doc_ref = sessions.document(document_id=session_cookie)
    transaction = db.transaction()
    transaction.set(doc_ref, data)
