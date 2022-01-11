from typing import Any, Dict, List, Tuple

from shared.helpers.util import ireg
from shared.search.functions import (SearchFilterLowercase, SearchFunctionDate, SearchFunctionExact, SearchFunctionInt,
                                     SearchFunctionString, SearchTransformerDelay)
from shared.search.syntax import SearchAnswer, SearchFilter, SearchFunction, SearchSyntax
from shared.search.tokenizer import SearchToken
from shared.types.deck import Deck


def ensure_author_join(ctx: dict) -> None:
    if 'author_joined' in ctx:
        return
    ctx['author_joined'] = 1
    ctx['pipeline'].append({'id': 'join_on_author', '$lookup': {
        'from': 'users', 'localField': 'author',
        'foreignField': 'user_id', 'as': 'a_author'
    }})
    ctx['pipeline'].append({'id': 'unwind_author', '$unwind': '$a_author'})
    ctx['pipeline'].append({'id': 'remove_author_id', '$unset': 'a_author._id'})


class SearchSyntaxDeck(SearchSyntax):
    def __init__(self) -> None:
        super().__init__('decks', 'name', Deck)
        self.add_filters()

    def add_filters(self) -> None:
        self.add_func('id', SearchFunctionString('deck_id'),
                      'Search the deck\'s ID.')
        self.add_func('name', SearchFunctionString('name'),
                      'Search the deck\'s name.', ['n'])
        self.add_func('author', SearchFunctionString('a_author.nickname')
                      .add_filter(SearchFilterAuthorJoin())
                      .add_transformer(SearchTransformerDelay()),
                      'Search the deck\'s author.', ['player', 'user', 'u'])
        self.add_func('competition', SearchFunctionString('competition'),
                      'Search the competition the deck was played in.', ['comp', 'source', 's', 'in'])
        self.add_func('format', SearchFunctionExact('format').add_filter(SearchFilterLowercase()),
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
        self.add_func('emainboard', SearchFunctionCard('mainboard_list', True),
                      'Search the cards in the mainboard of the deck with exact matching.', ['ecard', 'emd'])
        self.add_func('esideboard', SearchFunctionCard('sideboard_list', True),
                      'Search the cards in the sideboard of the deck with exact matching.', ['eside', 'esb'])

    @staticmethod
    def get_winrate_facet() -> List[Dict[str, Any]]:
        winrate = {'$group': {'_id': None, 'wins': {'$sum': '$wins'}, 'losses': {'$sum': '$losses'}}}
        return [winrate, {'$project': {'_id': 0}}]

    def parse(self, data: str, context: dict) -> Tuple[dict, dict]:
        d1, d2 = super().parse(data, context)
        context['facets']['winrate'] = self.get_winrate_facet()
        context['sort'].append('date~-1')
        context['sort'].append('deck_id~1')
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
    def __init__(self, field: str, exact: bool = False):
        super().__init__()
        self.field = field
        self.exact = exact
        self.add_filter(SearchFilterCardList())

    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        try:
            num = int(tok.magic)
        except ValueError:
            num = 1

        cmps = {'=': '$eq', '>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte', ':': '$eq'}
        base_dict = {'k': ireg(tok.value)} if not self.exact else {'k': ireg(f'^{tok.value}$')}
        if tok.comparator != ':':
            base_dict['v'] = {cmps[tok.comparator]: num}
        return {self.field: {'$elemMatch': base_dict}}, False


class SearchFilterAuthorJoin(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        ensure_author_join(context)
        return tok
