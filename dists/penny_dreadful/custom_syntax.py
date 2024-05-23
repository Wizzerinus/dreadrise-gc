from dists.penny_dreadful import constants
from shared.search.functions import (SearchFilterLowercase, SearchFunctionInt, SearchFunctionStringArray,
                                     SearchTransformerDelay)
from shared.search.syntax import SearchFilter
from shared.search.syntaxes.card import SearchSyntaxCard
from shared.search.syntaxes.deck import SearchSyntaxDeck
from shared.search.tokenizer import SearchToken
from shared.types.card import Card, CardFace

archetype_aliases = {
    'mba': 'mono-black-aggro',
    'rdw': 'red-deck-wins',
    'wgd': 'worldgorger-dragon',
    'mbr': 'mono-black-reanimator',
    'jac': 'jeskai-ascendancy',
    'jac3': 'jeskai-jeskai-ascendancy',
    'jac4': 'four-color-jeskai-ascendancy',
    'jac5': 'five-color-jeskai-ascendancy',
    'metalworks': 'anvil-colossus',
    'bluepost': 'mono-blue-cloudpost-control',
    'gates': 'guildgate-control',
    'mwc': 'mono-white-control',
    'esqpoe': 'life-is-ez',
    'mbm': 'mono-black-midrange'
}


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
        self.add_func('next', SearchFunctionInt('a_next_count.checks')
                      .add_filter(SearchFilterNextJoin())
                      .add_transformer(SearchTransformerDelay()),
                      'Search the confirmed legality in the next season.', ['n', 'ns'])

        for i in ['format', 'f', 'legal', 'l', 'restricted', 'banned', 'ban', 'not-legal', 'nl']:
            self.funcs[i][0].add_filter(SearchFilterPDFormat())


def ensure_archetype_children_join(ctx: dict) -> None:
    if 'archetype_children_joined' in ctx:
        return
    ctx['archetype_children_joined'] = 1
    ctx['pipeline'].append({'id': 'join_on_children', '$lookup': {
        'from': 'deck_tags', 'localField': 'tags.0',
        'foreignField': 'tag_id', 'as': 'a_tag_children'
    }})
    ctx['pipeline'].append({'id': 'unwind_children', '$unwind': '$a_tag_children'})
    ctx['pipeline'].append({'id': 'set_children', '$set': {'a_tag_children': '$a_tag_children.parents'}})


def ensure_next_join(ctx: dict) -> None:
    if 'next_joined' in ctx:
        return
    ctx['next_joined'] = 1
    ctx['pipeline'].append({'id': 'join_on_children', '$lookup': {
        'from': 'next_counts', 'localField': 'name',
        'foreignField': 'name', 'as': 'a_next_count'
    }})
    ctx['pipeline'].append({'id': 'unwind_next', '$unwind': '$a_next_count'})
    ctx['pipeline'].append({'id': 'unset_next_id', '$unset': 'a_next_count._id'})


class SearchSyntaxDeckPD(SearchSyntaxDeck):
    def __init__(self) -> None:
        super().__init__()
        self.add_filters_custom()

    def add_filters_custom(self) -> None:
        for i in ['format', 'f']:
            self.funcs[i][0].add_filter(SearchFilterPDFormat())

        self.replace_func('tags', SearchFunctionStringArray('a_tag_children')
                          .add_filter(SearchFilterLowercase())
                          .add_filter(SearchFilterArchetypeTree())
                          .add_filter(SearchFilterArchetypeAliases())
                          .add_transformer(SearchTransformerDelay()))


class SearchFilterArchetypeTree(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        ensure_archetype_children_join(context)
        return tok


class SearchFilterNextJoin(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        ensure_next_join(context)
        return tok


class SearchFilterArchetypeAliases(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        tok.value = archetype_aliases.get(tok.value, tok.value)
        return tok


produces_exclusions = {'Old-Growth Dryads'}


class PDCardFace(CardFace):
    def process_produces(self) -> None:
        if self.name in produces_exclusions:
            self.produces = []
            self.produces_len = 0
            return

        super().process_produces()


class PDCard(Card):
    # faces: list[PDCardFace]
    # fixed_faces: list[PDCardFace]
    # This doesn't work within MyPy for reasons I don't understand
    ftime: int
    ltime: int
