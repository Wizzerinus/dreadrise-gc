from dists.penny_dreadful import constants
from shared.search.functions import SearchFunctionInt
from shared.search.syntax import SearchFilter
from shared.search.syntaxes.card import SearchSyntaxCard
from shared.search.syntaxes.deck import SearchSyntaxDeck
from shared.search.tokenizer import SearchToken
from shared.types.card import Card


class SearchFilterPDFormat(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        if tok.value in ['pd', 'penny']:
            tok.value = 'pds' + str(constants.pd_data['last_season'])
        if tok.value in ['eternal', 'pds_x', 'pdeternal']:
            tok.value = 'pdsx'
        return tok


class SearchSyntaxCardPD(SearchSyntaxCard):
    def __init__(self) -> None:
        super().__init__()
        self.add_filters_custom()

    def add_filters_custom(self) -> None:
        self.add_func('first-time', SearchFunctionInt('ftime'),
                      'Search the first time the card has been legal in PD.', ['ftime', 'ft'])
        self.add_func('last-time', SearchFunctionInt('ltime'),
                      'Search the last time the card has been legal in PD.', ['ltime', 'lt'])

        for i in ['format', 'f', 'legal', 'l', 'restricted', 'banned', 'ban', 'not-legal', 'nl']:
            self.funcs[i][0].add_filter(SearchFilterPDFormat())


class SearchSyntaxDeckPD(SearchSyntaxDeck):
    def __init__(self) -> None:
        super().__init__()
        self.add_filters_custom()

    def add_filters_custom(self) -> None:
        for i in ['format', 'f']:
            self.funcs[i][0].add_filter(SearchFilterPDFormat())


class PDCard(Card):
    ftime: int
    ltime: int
