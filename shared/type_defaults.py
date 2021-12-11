import datetime
import logging

from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag
from shared.types.user import User

logger = logging.getLogger('dreadrise.util.type_defaults')


def get_blank_user(u: str) -> User:
    # logger.warning(f'Generating blank user for {u}')
    return User().load({
        'user_id': u,
        'nickname': u,
        'privileges': {}
    })


default_tag = DeckTag().load({
    'tag_id': 'unknown',
    'name': 'Unknown',
    'description': 'Unknown tag',
    'archetype': 'unclassified'
})


bye_user = User().load({
    'user_id': 'bye',
    'nickname': 'Bye',
    'privileges': {}
})


default_deck = Deck().load({
    'deck_name': 'Unknown deck',
    'deck_id': '',
    'mainboard': {'Island': 60},
    'sideboard': {},
    'author': 'unknown',
    'games': [],
    'wins': 0, 'losses': 0, 'ties': 0,
    'date': datetime.datetime.now()
})


def make_card(name: str) -> Card:
    return Card().load({
        'name': name,
        'card_id': '',
        'layout': 'normal',
        'oracle': '',
        'faces': [{
            'name': name
        }]
    })
