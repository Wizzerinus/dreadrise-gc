from typing import Dict

from pymongo import MongoClient
from pymongo.database import Database

from shared.core_enums import Distribution
from shared.helpers import configuration
from shared.helpers.exceptions import ConfigurationError

mongo_clients: Dict[Distribution, Database] = {}


def setup_indexes(d: Database) -> None:
    """
    Sets up indexes required for optimal DB functioning.
    :param d: the Database object
    :return: nothing
    """
    d.cards.create_index('name', unique=True, name='card name')
    d.cards.create_index('card_id', unique=True, name='card ID')
    d.decks.create_index('deck_id', unique=True, name='deck ID')
    d.deck_tags.create_index('tag_id', unique=True, name='tag ID')
    d.deck_tags.create_index('name', unique=True, name='tag name')
    d.text_deck_rules.create_index('tag_id', name='text deck tag')
    d.text_deck_rules.create_index('rule_id', unique=True, name='rule ID for text')
    d.color_deck_rules.create_index('rule_id', unique=True, name='rule ID for color')
    d.users.create_index('login', unique=True, sparse=True, name='user login')
    d.users.create_index('user_id', unique=True, name='user ID')
    d.users.create_index('nickname', unique=True, sparse=True, name='user nickname I')
    d.expansions.create_index('code', unique=True, name='expansion code')


def connect(dist: Distribution) -> Database:
    """
    Returns the database client for a certain distribution
    :param dist: the distribution
    :return: the Database object
    """
    if dist not in mongo_clients:
        connection_str = configuration.get('MONGODB_URL', dist)
        if not connection_str:
            raise ConfigurationError(f'Distribution {dist} does not exist')
        mc = MongoClient(host=connection_str)
        db_name = connection_str.split('/')[-1]
        mongo_clients[dist] = mc.get_database(db_name)  # type: ignore
        setup_indexes(mongo_clients[dist])

    return mongo_clients[dist]
