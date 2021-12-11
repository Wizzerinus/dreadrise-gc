import logging
import os
from typing import Dict, Optional

import yaml

from shared.core_enums import Distribution, distributions
from shared.helpers.exceptions import ConfigurationError
from shared.helpers.util import int_def

logger = logging.getLogger('dreadrise.configuration')

cache: Dict[str, Dict[str, str]] = {}


def _merge(i: Optional[Dict[str, str]], j: Dict[str, str]) -> Dict[str, str]:
    if not i:
        return j

    for k, v in i.items():
        if k not in j:
            j[k] = v
    return j


def _preload_directory(directory: str, distribution: str) -> Dict[str, str]:
    core = {}
    for i, j in os.environ.items():
        if i.startswith(f'{distribution}__'):
            core[i.split('__')[1]] = j
    try:
        logger.info(f'Loading secrets from {directory}')
        with open(f'{directory}/secrets.yml') as f:
            core = _merge(yaml.load(f, yaml.SafeLoader), core)
    except FileNotFoundError:
        logger.warning(f'Secrets in {directory} not found')

    with open(f'{directory}/core.yml') as f:
        logger.info(f'Loading core configuration from {directory}')
        core = _merge(yaml.load(f, yaml.SafeLoader), core)
    return core


def _preload() -> None:
    if cache:
        return
    logger.info('Preloading configuration settings')
    cache['default'] = _preload_directory('config', 'default')
    for i in distributions:
        if i != 'default':
            cache[i] = _merge(cache['default'], _preload_directory(f'config/dist/{i}', i))
    logger.info('Finished preloading configuration')


def get(name: str, dist: Distribution = 'default') -> str:
    """
    Returns configuration variable. Raises an exception if it doesn't exist.
    :param name: the variable to fetch
    :param dist: the active distribution
    :return: the variable value
    """
    _preload()
    if name not in cache[dist]:
        raise ConfigurationError(f'Key {name} not found in environmental variables or configuration files.')
    return cache[dist][name]


def get_int(name: str, dist: Distribution = 'default') -> int:
    """
    Returns configuration variable as a number. 0 if it's not a number. Raises an exception if it doesn't exist.
    :param name: the variable to fetch
    :param dist: the active distribution
    :return: the variable value
    """
    return int_def(get(name, dist))
