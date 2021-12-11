from typing import Callable, Dict, List, Literal, Set, Tuple, Type

from shared.search.syntaxes.abstract import SearchSyntaxCardAbstract, SearchSyntaxDeckAbstract
from shared.types.card import Card
from shared.types.deck import Deck

FormatModule = Literal['admin', 'archetyping', 'cropping']


class DistConstants:
    """
        The distribution constants file. Should be put into /dists/{dist_id}/constants.

        Attributes:
            formats: List of all formats managed by this distribution.
            scraped_formats: List of all formats which have decks managed by this distribution.
            format_localization: Dictionary with keys being format IDs, and values being humanized format names.
            default_format: The default format managed by this distribution. Used to show the relevant decks.
            enabled_modules: The optional modules managed by this format.
            category_descriptions: List of all card categories. Used in card search. Consists of tuples,
            with first element being category ID, and the second category description.
            card_search_syntax: Class providing the card search for this distribution.
            default_card: The card used for this distribution by default, if the most popular card isn't known.
            deck_checkers: List of the deck checkers, used by the deck editor.
            get_rotation_angle: Function which returns the angle the card should be rotated by.
            get_sideboard_importance: Function which takes a sideboard card, and the count of it in the sideboard,
            and returns how important is that card, at the scale 1 = 1 mainboard copy, 4 = mainboard playset
            (e.g. companions, first mates, etc)
            get_crop_location: Function which returns the cropped art location of a card.
            Only used if the art module is disabled.
            index_types: Types of competitions to be shown on index
            get_deck_weight: Function which returns the importance of the deck. The deck with the highest weight
            is shown as the example deck of the archetype
            new_deck_formats: list of format IDs decks for which can be created
    """
    formats: List[str]
    scraped_formats: List[str]
    format_localization: Dict[str, str]
    default_format: str
    enabled_modules: Set[FormatModule]
    category_descriptions: List[Tuple[str, str]]
    card_search_syntax: Type[SearchSyntaxCardAbstract]
    deck_search_syntax: Type[SearchSyntaxDeckAbstract]
    default_card: str
    deck_checkers: List[Callable[[Deck, Dict[str, Card]],
                                 Tuple[Literal['Success!', 'Warnings found!', 'Errors found!'], str]]]

    @staticmethod
    def get_rotation_angle(c: Card) -> Literal[0, 90, 180, 270]:
        pass

    @staticmethod
    def get_sideboard_importance(c: Card, i: int) -> int:
        pass

    @staticmethod
    def get_crop_location(c: Card) -> str:
        pass

    @staticmethod
    def get_deck_weight(d: Deck) -> float:
        pass

    index_types: List[str]
    new_deck_formats: List[str]
