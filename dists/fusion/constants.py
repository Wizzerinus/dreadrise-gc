from dists.fusion.checking import check_fusion_legality
from dists.fusion.custom_syntax import FusionCard, SearchSyntaxCardFusion
from dists.msem.checking import (check_adam, check_alvarez, check_asabeth, check_ashe, check_garth, check_harriet,
                                 check_holcomb, check_hugo, check_lilia, check_mable, check_marisa, check_searle,
                                 check_tabia, check_telsi, check_tinbeard, check_valencia, check_vir)
from dists.msem.constants import CategoryDescriptions as MSEMCat
from dists.msem.constants import GetRotationAngle as MSEMAngle
from dists.msem.constants import GetSideboardImportance as MSEMSide
from dists.penny_dreadful.checking import (check_gyruda, check_jegantha, check_kaheera, check_keruga, check_lurrus,
                                           check_lutri, check_obosh, check_umori, check_yorion, check_zirda)
from dists.penny_dreadful.constants import CategoryDescriptions as PDCat
from dists.penny_dreadful.constants import GetRotationAngle as PDAngle
from dists.penny_dreadful.constants import GetSideboardImportance as PDSide
from shared.helpers.deckcheck.default import (check_general_legality, check_maindeck_size, check_max_count,
                                              check_restricted_list, check_sideboard_size)
from shared.search.syntaxes.deck import SearchSyntaxDeck
from shared.types.deck import Deck

Formats = ['vintage', 'legacy', 'modern', 'pioneer', 'msem', 'fusion']
NewDeckFormats = ['fusion', 'freeform']
ScrapedFormats = ['fusion']
FormatLocalization = {
    'vintage': 'Vintage',
    'legacy': 'Legacy',
    'modern': 'Modern',
    'pioneer': 'Pioneer',
    'msem': 'MSEM',
    'freeform': 'Freeform',
    'fusion': 'Fusion',
}

DefaultFormat = 'fusion'
EnabledModules = {'cropping'}

CategoryDescriptions = PDCat + MSEMCat
CardSearchSyntax = SearchSyntaxCardFusion
DeckSearchSyntax = SearchSyntaxDeck
DefaultCard = 'panya-of-lands-unknown'

DeckCheckers = [
    check_adam, check_tabia, check_mable, check_marisa, check_hugo, check_garth, check_harriet,
    check_holcomb, check_searle, check_alvarez, check_valencia,
    check_general_legality, check_sideboard_size, check_maindeck_size, check_max_count,
    check_asabeth, check_ashe, check_telsi, check_lilia, check_tinbeard, check_vir,
    check_gyruda, check_jegantha, check_kaheera, check_keruga, check_lurrus,
    check_lutri, check_obosh, check_umori, check_yorion, check_zirda, check_restricted_list,
    check_fusion_legality
]

IndexTypes: list[str] = []


def GetRotationAngle(c: FusionCard, face_index: int = 0) -> int:
    return MSEMAngle(c) if c.database == 'custom' else PDAngle(c)


def GetSideboardImportance(c: FusionCard, w: int) -> int:
    return MSEMSide(c, w) if c.database == 'custom' else PDSide(c, w)


def GetDeckWeight(deck: Deck) -> float:
    return deck.wins - deck.losses * 0.55
