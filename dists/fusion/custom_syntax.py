from typing import Literal

from shared.search.functions import SearchFunctionString
from shared.search.syntaxes.card import SearchSyntaxCard
from shared.types.card import Card


class SearchSyntaxCardFusion(SearchSyntaxCard):
    def __init__(self) -> None:
        super().__init__()
        self.add_func('database', SearchFunctionString('database'),
                      'Search the database the card is in.', ['db'])


class FusionCard(Card):
    database: Literal['canon', 'custom'] = 'canon'
