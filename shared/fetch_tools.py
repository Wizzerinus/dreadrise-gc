import json
import logging
import time
import urllib.request
from typing import Any, cast

import requests

from shared.helpers.exceptions import FetchError

logger = logging.getLogger('dreadrise.fetcher')


def fetch_core(url: str, character_encoding: str | None = None, force: bool = False, retry: bool = True,
               session: requests.Session | None = None, is_bytes: bool = False) -> str | bytes:
    headers = {}
    if force:
        headers['Cache-Control'] = 'no-cache'
    logger.info('Fetching {url} ({cache})'.format(url=url, cache='no cache' if force else 'cache ok'))
    if 'file:///' in url:
        logger.warning('Loading a locally saved file because file:/// was provided')
        with open(url[7:]) as file:
            return file.read()
    try:
        if session is not None:
            response = session.get(url, headers=headers)
        else:
            response = requests.get(url, headers=headers)
        if character_encoding is not None:
            response.encoding = character_encoding

        if response.status_code in [500, 502, 503]:
            raise FetchError(f'Server returned a {response.status_code} from {url}')
        logger.info(f'Fetching {url} done')
        return response.text if not is_bytes else response.content
    except FetchError as e:
        if "502" in str(e) and retry:
            logger.warning('Got a 502 Bad Gateway, retrying in 5 seconds')
            time.sleep(5)
            return fetch_core(url, character_encoding, force, False, session, is_bytes)
        raise e from e
    except (urllib.error.HTTPError, requests.exceptions.ConnectionError, TimeoutError) as e:  # type: ignore
        if retry:
            logger.warning(f'Fetch {url} failed, retrying')
            return fetch_core(url, character_encoding, force, False, session, is_bytes)
        raise FetchError(e) from e


def fetch_str(*args: Any, **kwargs: Any) -> str:
    kwargs['is_bytes'] = False
    return cast(str, fetch_core(*args, **kwargs))


def fetch_bytes(*args: Any, **kwargs: Any) -> bytes:
    kwargs['is_bytes'] = True
    return cast(bytes, fetch_core(*args, **kwargs))


def fetch_json(url: str, character_encoding: str | None = None, session: requests.Session | None = None) -> Any:
    try:
        blob = fetch_core(url, character_encoding, session=session)
        if blob:
            return json.loads(blob)
        return None
    except json.decoder.JSONDecodeError as e:
        raise FetchError(e) from e


def post(url: str, data: dict[str, str] | None = None, json_data: Any = None) -> str:
    logger.info(f'POSTing to {url} with {data} / {json_data}')
    try:
        response = requests.post(url, data=data, json=json_data)
        return response.text
    except requests.exceptions.ConnectionError as e:
        raise FetchError(e) from e


def store(url: str, path: str) -> requests.Response:
    logger.info(f'Storing {url} in {path}')
    try:
        response = requests.get(url, stream=True)
        with open(path, 'wb') as fout:
            for chunk in response.iter_content(1024):
                fout.write(chunk)
        return response
    except urllib.error.HTTPError as e:
        raise FetchError(e) from e
    except requests.exceptions.ConnectionError as e:
        raise FetchError(e) from e


def escape(str_input: str, skip_double_slash: bool = False) -> str:
    # Expand 'AE' into two characters. This matches the legal list and
    # WotC's naming scheme in Kaladesh, and is compatible with the
    # image server and scryfall.
    s = str_input
    if skip_double_slash:
        s = s.replace('//', '-split-')
    s = urllib.parse.quote_plus(s.replace(u'Æ', 'AE')).lower()  # type: ignore # urllib isn't fully stubbed
    if skip_double_slash:
        s = s.replace('-split-', '//')
    return s
