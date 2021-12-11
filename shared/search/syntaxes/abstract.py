from abc import ABC

from shared.search.syntax import SearchSyntax
from shared.types.card import Card
from shared.types.deck import Deck


class SearchSyntaxCardAbstract(SearchSyntax[Card], ABC):
    def __init__(self) -> None:
        super().__init__('a', 'b', Card)


class SearchSyntaxDeckAbstract(SearchSyntax[Deck], ABC):
    def __init__(self) -> None:
        super().__init__('a', 'b', Deck)
