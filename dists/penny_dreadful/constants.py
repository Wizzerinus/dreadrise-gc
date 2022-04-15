import logging

from shared import fetch_tools
from shared.helpers.deckcheck.default import (check_general_legality, check_maindeck_size, check_max_count,
                                              check_restricted_list, check_sideboard_size)
from shared.helpers.exceptions import FetchError
from shared.types.card import Card
from shared.types.deck import Deck

from .checking import (check_gyruda, check_jegantha, check_kaheera, check_keruga, check_lurrus, check_lutri,
                       check_obosh, check_umori, check_yorion, check_zirda)
from .custom_syntax import SearchSyntaxCardPD, SearchSyntaxDeckPD
from .gateway import parse

logger = logging.getLogger('dreadrise.dist.pd')

Formats = ['vintage', 'legacy', 'modern', 'pioneer', 'pdsx']
NewDeckFormats = ['vintage', 'legacy', 'modern', 'pioneer', 'pdsx']
ScrapedFormats = []
FormatLocalization = {
    'vintage': 'Vintage',
    'legacy': 'Legacy',
    'modern': 'Modern',
    'pioneer': 'Pioneer',
    'pdsx': 'PD Eternal'
}

pd_data = {'last_season': 0}
DefaultFormat = 'pdsx'

EnabledModules = {'gateway'}


def Update() -> None:
    global DefaultFormat
    if pd_data['last_season'] > 0:
        logger.warning('Skipping update')
        return

    season_code_url = 'https://pennydreadfulmagic.com/api/seasoncodes'
    try:
        x = pd_data['last_season'] = len(fetch_tools.fetch_json(season_code_url))
        logger.info(f'Last PD season: {x}')
    except FetchError:
        x = 23
        logger.warning('Using a placeholder PD season')

    for i in range(1, pd_data['last_season'] + 1):
        Formats.append(f'pds{i}')
        ScrapedFormats.append(f'pds{i}')
        FormatLocalization[f'pds{i}'] = f'PD Season {i}'
    DefaultFormat = f'pds{x}'
    NewDeckFormats.append(DefaultFormat)
    logger.info('Update complete.')


competition_types = ['league', 'tournament', 'kickoff', 'pd500']
competition_localization = {
    'league': 'League',
    'tournament': 'Gatherling',
    'kickoff': 'PD Kickoff',
    'pd500': 'PD 500'
}

CategoryDescriptions = [
    ('bicycle', 'Dual lands that can be cycled'),
    ('tricycle', '3-color lands that can be cycled'),
    ('bounceland', 'Lands that bounce other lands when they enter'),
    ('canopyland', 'Lands from Horizon Canopy cycle'),
    ('checkland', 'Lands that check for basic land types'),
    ('true-dual', 'True dual lands'),
    ('fastland', 'Lands that enter untapped if two or less other lands are in play'),
    ('fetchland', 'Lands that fetch other lands for life'),
    ('slowfetch', 'Lands that slowly fetch other lands'),
    ('filterland', 'Lands that filter mana'),
    ('gainland', 'Lands that gain life when they enter'),
    ('reveal-land', 'Lands that enter untapped if their controller reveals a card from their hand'),
    ('painland', 'Dual lands that deal damage when tapped for colored mana'),
    ('scryland', 'Dual lands that scry when they enter'),
    ('shockland', 'Lands that shock their controller to enter untapped'),
    ('manland', 'Lands that can become creatures'),
    ('triland', '3-color lands without other abilities'),
    ('tangoland', 'Typed lands that check for two basics'),
    ('slowland', 'Nontyped lands that check for two lands'),
    ('storageland', 'Lands that can store mana'),

    ('fetchable', 'Lands that can be fetched'),

    ('power', 'The Power Nine'),
    ('power2', 'The Extended Power Nine'),
    ('spell', 'Cards that can be cast as spells'),
    ('permanent', 'Cards that can be played as permanents'),
    ('historic', 'The historic cards'),
    ('companion', 'Cards that can be the player\'s companion'),

    ('jegantha', 'Cards legal with Jegantha, the Wellspring companion'),
    ('zirda', 'Cards legal with Zirda, the Dawnwaker companion'),
    ('lurrus', 'Cards legal with Lurrus of the Dream-Den companion'),
    ('kaheera', 'Cards legal with Kaheera, the Orphanguard companion'),
    ('obosh', 'Cards legal with Obosh, the Preypiercer companion'),
    ('gyruda', 'Cards legal with Gyruda, Doom of Depths companion'),
    ('keruga', 'Cards legal with Keruga, the Macrosage companion')
]

CardSearchSyntax = SearchSyntaxCardPD
DeckSearchSyntax = SearchSyntaxDeckPD
DefaultCard = 'enter-the-infinite'


def GetCropLocation(card: Card) -> str:
    return card.image.replace('/normal/', '/art_crop/')


DeckCheckers = [check_sideboard_size, check_maindeck_size, check_max_count, check_general_legality,
                check_gyruda, check_jegantha, check_kaheera, check_keruga, check_lurrus,
                check_lutri, check_obosh, check_umori, check_yorion, check_zirda, check_restricted_list]

IndexTypes = ['kickoff', 'pd500']


def GetRotationAngle(c: Card) -> int:
    return 270 if c.layout == 'split' and 'Aftermath' not in c.faces[1].oracle else 0


def GetSideboardImportance(c: Card, w: int) -> int:
    return 3 if 'companion' in c.categories else 0


def GetDeckWeight(deck: Deck) -> float:
    base = {'league': -1, 'tournament': 0, 'kickoff': 0.5, 'pd500': 1}[deck.source]
    return base + deck.wins - deck.losses * 0.55


ParseGateway = parse
