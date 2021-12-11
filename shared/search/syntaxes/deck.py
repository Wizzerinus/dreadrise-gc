from typing import Any, Dict, List, Tuple

from shared.helpers.util import ireg
from shared.search.functions import SearchFunctionDate, SearchFunctionInt, SearchFunctionString
from shared.search.syntax import SearchAnswer, SearchFilter, SearchFunction, SearchSyntax
from shared.search.tokenizer import SearchToken
from shared.types.deck import Deck


class SearchSyntaxDeck(SearchSyntax):
    def __init__(self) -> None:
        super().__init__('decks', 'name', Deck)
        self.add_filters()

    def add_filters(self) -> None:
        self.add_func('id', SearchFunctionString('deck_id'),
                      'Search the deck\'s ID.')
        self.add_func('name', SearchFunctionString('name'),
                      'Search the deck\'s name.', ['n'])
        self.add_func('author', SearchFunctionString('author'),
                      'Search the deck\'s author.', ['player', 'user', 'u'])
        self.add_func('competition', SearchFunctionString('competition'),
                      'Search the competition the deck was played in.', ['comp', 'source', 's', 'in'])
        self.add_func('format', SearchFunctionString('format'),
                      'Search the format the deck was played in.', ['f'])
        self.add_func('date', SearchFunctionDate('date'),
                      'Search the date the deck was played at.', ['time'])
        self.add_func('tags', SearchFunctionString('tags'),
                      'Search the tags/archetypes the deck has.', ['archetypes', 'tag', 'arch'])
        self.add_func('wins', SearchFunctionInt('wins'),
                      'Search the number of wins the deck has.', ['win', 'w'])
        self.add_func('losses', SearchFunctionInt('losses'),
                      'Search the number of losses the deck has.', ['loss', 'l'])
        self.add_func('mainboard', SearchFunctionCard('mainboard_list'),
                      'Search the cards in the mainboard of the deck.', ['main', 'card', 'maindeck', 'md'])
        self.add_func('sideboard', SearchFunctionCard('sideboard_list'),
                      'Search the cards in the sideboard of the deck.', ['side', 'sb'])

    @staticmethod
    def get_winrate_facet() -> List[Dict[str, Any]]:
        winrate = {'$group': {'_id': None, 'wins': {'$sum': '$wins'}, 'losses': {'$sum': '$losses'}}}
        return [winrate, {'$project': {'_id': 0}}]

    def parse(self, data: str, context: dict) -> Tuple[dict, dict]:
        d1, d2 = super().parse(data, context)
        context['facets']['winrate'] = self.get_winrate_facet()
        context['sort'].append('deck_id~-1')
        return {'$and': [{'competition': {'$exists': 1}}, d1]}, d2


def ensure_card_list(ctx: dict) -> None:
    if 'card_list' in ctx:
        return
    ctx['card_list'] = 1
    ctx['pipeline'].append({'id': 'create_card_list', '$addFields': {
        'mainboard_list': {'$objectToArray': '$mainboard'},
        'sideboard_list': {'$objectToArray': '$sideboard'}
    }})


class SearchFilterCardList(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        ensure_card_list(context)
        return tok


class SearchFunctionCard(SearchFunction):
    def __init__(self, field: str):
        super().__init__()
        self.field = field
        self.add_filter(SearchFilterCardList())

    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        try:
            num = int(tok.magic)
        except ValueError:
            num = 1

        cmps = {'=': '$eq', '>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte', ':': '$eq'}
        if tok.comparator != ':':
            base_dict = {'k': ireg(tok.value), 'v': {cmps[tok.comparator]: num}}
        else:
            base_dict = {'k': ireg(tok.value)}
        return {self.field: {'$elemMatch': base_dict}}, False
