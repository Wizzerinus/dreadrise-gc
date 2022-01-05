from shared.helpers.deckcheck.default import (check_general_legality, check_maindeck_size, check_max_count,
                                              check_sideboard_size)
from shared.search.syntaxes.card import SearchSyntaxCard
from shared.search.syntaxes.deck import SearchSyntaxDeck
from shared.types.card import Card
from shared.types.deck import Deck

from .checking import (check_adam, check_alvarez, check_garth, check_harriet, check_holcomb, check_hugo, check_mable,
                       check_marisa, check_searle, check_tabia, check_valencia)
from .gateway import parse

formats = ['freeform', 'msem', 'msedh']
new_deck_formats = ['freeform', 'msem', 'msedh']
default_format = 'msem'
format_localization = {
    'freeform': 'Freeform',
    'msem': 'MSEM',
    'msedh': 'MSEDH'
}

competition_types = ['gp', 'league']
competition_localization = {
    'gp': 'Grand Prix',
    'league': 'League'
}

scraped_formats = ['msem']
enabled_modules = {'admin', 'archetyping', 'cropping', 'gateway'}

category_descriptions = [
    ('hugo', 'Can be put into decks with Hugo of the Shadowstaff First Mate'),
    ('mable', 'Can be put into decks with Mable of the Sea\'s Whimsy First Mate'),
    ('marisa', 'Can be put into decks with Marisa of the Gravehowl First Mate'),
    ('searle', 'Can be put into decks with Searle of the Tempest First Mate'),
    ('garth', 'Can be put into decks with Garth of the Chimera First Mate'),

    ('modal', 'Modal spells and permanents'),
    ('storied', 'Storied spells and permanents'),
    ('cryptic', 'Cryptic spells and permanents'),
    ('first-mate', 'Cards that can be your first mate'),
    ('cane-dancer', 'Cards that can be flashed back with Cane Dancer'),

    ('abandoned', 'Lands that enter untapped if their controller has no other nonbasics'),
    ('angeltouched', 'Trilands which cannot be used to cast single-color spells'),
    ('filterland', 'Lands that filter colorless mana into mana of two colors'),
    ('auroraland', 'Legendary lands that can be exiled from hand to cast a massive spell'),
    ('tricheck', 'Two-color lands that enter untapped if a land of a third type is present'),
    ('colorfetch', 'Fetches that can produce colored mana'),
    ('desert-manland', 'Deserts that can become creatures'),
    ('clue-painland', 'Painlands that can be sacrificed to investigate'),
    ('edhland', 'Lands that enter untapped if the player has multiple opponents'),
    ('painland', 'Classic painlands'),
    ('shadowland', 'Shadowlands/Snarls'),
    ('shiftland', 'Pseudo-fetchlands that produce colorless mana on the first turn'),
    ('shockfetch', 'Fetchlands that enter untapped if their controller pays 2 life'),
    ('sunriseland', 'Lands that can be untapped during each opponent\'s untap step'),
    ('tormentland', 'Lands that torment their controller to enter untapped'),
    ('animus', 'Fetchable lands that can turn into creatures'),
    ('koraland', 'Lands that check for basics with their land types to enter untapped'),
    ('plagueland', 'Typed lands that cause their controller to lose life if that player has less than two basics'),
    ('typed-triland', 'Trilands with card types')
]

card_search_syntax = SearchSyntaxCard
deck_search_syntax = SearchSyntaxDeck
default_card = 'into-the-unknown'

deck_checkers = [check_adam, check_tabia, check_mable, check_marisa, check_hugo, check_garth, check_harriet,
                 check_holcomb, check_searle, check_alvarez, check_valencia,
                 check_general_legality, check_sideboard_size, check_maindeck_size, check_max_count]

index_types = ['gp']


def get_rotation_angle(c: Card) -> int:
    return 0


def get_sideboard_importance(c: Card, w: int) -> int:
    return 5 if 'first-mate' in c.categories else 0


def get_deck_weight(deck: Deck) -> float:
    base = {'league': -1, 'gp': 0}[deck.source]
    return base + deck.wins - deck.losses * 0.55


parse_gateway = parse
