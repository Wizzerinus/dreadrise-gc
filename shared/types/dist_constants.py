from typing import Callable, Dict, List, Literal, Set, Tuple, Type

from shared.search.syntaxes.abstract import SearchSyntaxCardAbstract, SearchSyntaxDeckAbstract
from shared.types.card import Card
from shared.types.deck import Deck

FormatModule = Literal['admin', 'archetyping', 'cropping']


class DistConstants:
    """
        The distribution constants file. Should be put into /dists/{dist_id}/constants.

        Attributes:
            Formats: List of all formats managed by this distribution.
            ScrapedFormats: List of all formats which have decks managed by this distribution.
            FormatLocalization: Dictionary with keys being format IDs, and values being humanized format names.
            DefaultFormat: The default format managed by this distribution. Used to show the relevant decks.
            EnabledModules: The optional modules managed by this format.
            CategoryDescriptions: List of all card categories. Used in card search. Consists of tuples,
            with first element being category ID, and the second category description.
            CardSearchSyntax: Class providing the card search for this distribution.
            DefaultCard: The card used for this distribution by default, if the most popular card isn't known.
            DeckCheckers: List of the deck checkers, used by the deck editor.
            GetRotationAngle: Function which returns the angle the card should be rotated by.
            GetSideboardImportance: Function which takes a sideboard card, and the count of it in the sideboard,
            and returns how important is that card, at the scale 1 = 1 mainboard copy, 4 = mainboard playset
            (e.g. companions, first mates, etc)
            GetCropLocation: Function which returns the cropped art location of a card.
            Only used if the art module is disabled.
            IndexTypes: Types of competitions to be shown on index
            GetDeckWeight: Function which returns the importance of the deck. The deck with the highest weight
            is shown as the example deck of the archetype
            NewDeckFormats: list of format IDs decks for which can be created
            Update: is called when the server is initialized
            ParseGateway: Parses a gateway query. The query will include the "gateway_key" field (checked at top level)
            and the "action" field (must be checked by the distribution). The output must include "success" (bool)
            and "reason" if success=false.
    """
    Formats: List[str]
    ScrapedFormats: List[str]
    FormatLocalization: Dict[str, str]
    DefaultFormat: str
    EnabledModules: Set[FormatModule]
    CategoryDescriptions: List[Tuple[str, str]]
    CardSearchSyntax: Type[SearchSyntaxCardAbstract]
    DeckSearchSyntax: Type[SearchSyntaxDeckAbstract]
    DefaultCard: str
    DeckCheckers: List[Callable[[Deck, Dict[str, Card]],
                                Tuple[Literal['Success!', 'Warnings found!', 'Errors found!'], str]]]

    @staticmethod
    def GetRotationAngle(c: Card) -> Literal[0, 90, 180, 270]:
        pass

    @staticmethod
    def GetSideboardImportance(c: Card, i: int) -> int:
        pass

    @staticmethod
    def GetCropLocation(c: Card) -> str:
        pass

    @staticmethod
    def GetDeckWeight(d: Deck) -> float:
        pass

    @staticmethod
    def Update() -> None:
        pass

    @staticmethod
    def ParseGateway(data: dict) -> dict:
        pass

    IndexTypes: List[str]
    NewDeckFormats: List[str]
