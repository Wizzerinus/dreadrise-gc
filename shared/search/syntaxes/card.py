from typing import Dict, List, Optional, Tuple, Union, cast

from shared.card_enums import mana_symbols
from shared.helpers.exceptions import SearchDataError
from shared.helpers.magic import get_rarity
from shared.helpers.mana_parsing import get_mana_cost
from shared.helpers.util import ireg
from shared.search.functions import (SearchFilterFunction, SearchFilterLowercase, SearchFunction,
                                     SearchFunctionArrayValidator, SearchFunctionColor, SearchFunctionExact,
                                     SearchFunctionFloat, SearchFunctionInt, SearchFunctionString,
                                     SearchTransformerDelay)
from shared.search.renamer import rename_query
from shared.search.syntax import SearchAnswer, SearchFilter, SearchSyntax
from shared.search.tokenizer import SearchGroup, SearchToken
from shared.types.card import Card


class SearchFunctionOracle(SearchFunction):
    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        name = 'oracle' if '~' not in tok.value else 't_oracle'  # I really should move from singleton functions...
        val = tok.value if tok.comparator != '=' else f'^{tok.value}$'
        return {name: {'$regex': val, '$options': 'i'}}


class SearchFunctionLegality(SearchFunction):
    def __init__(self, targets: List[str]):
        super().__init__()
        self.tgts = targets

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        obj = self.tgts[0] if len(self.tgts) == 1 else {'$in': self.tgts}
        return {f'legality.{tok.value}': obj}


class SearchFilterProduces(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        if tok.comparator == ':':
            tok.comparator = '>='
        return tok


class SearchFunctionManaCost(SearchFunctionArrayValidator):
    def __init__(self) -> None:
        super().__init__(list(mana_symbols))

    @staticmethod
    def parse(target: str, tok: SearchToken) -> int:
        if target == 'generic':
            ints = [x for x in tok.value if isinstance(x, int)]
            return sum(ints)
        return len([x for x in tok.value if x == target])

    # the token will be like:
    # [4, 'green', 'green', 'black']
    # and the target will be 'generic' or a color
    def greater_or_equal(self, target: str, tok: SearchToken) -> dict:
        count = self.parse(target, tok)
        return {f'mana_cost.{target}': {'$gte': count}}

    def greater(self, target: str, tok: SearchToken) -> dict:
        count = self.parse(target, tok)
        return {f'mana_cost.{target}': {'$gt': count}}

    def exists(self, target: str, tok: SearchToken) -> dict:
        return {f'mana_cost.{target}': {'$exists': 1}}

    def contains(self, target: str, tok: SearchToken) -> bool:
        count = self.parse(target, tok)
        return count > 0


def ensure_playability_join(ctx: dict) -> None:
    if 'playability_joined' in ctx:
        return
    ctx['playability_joined'] = 1
    ctx['pipeline'].append({'id': 'join_on_playability', '$lookup': {
        'from': 'card_playability', 'localField': 'name',
        'foreignField': 'card_name', 'as': 'a_playability'
    }})
    ctx['pipeline'].append({'id': 'unwind_playability', '$unwind': '$a_playability'})
    ctx['pipeline'].append({'id': 'match_playability_f', '$match': {'a_playability.format': '_all'}})
    ctx['pipeline'].append({'id': 'remove_playability_id', '$unset': 'a_playability._id'})


def ensure_expansion_join(ctx: dict) -> None:
    if 'expansion_joined' in ctx:
        return
    ctx['expansion_joined'] = 1
    ctx['pipeline'].append({'id': 'join_on_expansion', '$lookup': {
        'from': 'expansions', 'localField': 'sets',
        'foreignField': 'code', 'as': 'a_sets'
    }})
    ctx['pipeline'].append({'id': 'remove_expansion_id', '$unset': 'a_sets._id'})


def ensure_latest_expansion(ctx: dict) -> None:
    if 'latest_expansion_joined' in ctx:
        return
    ensure_expansion_join(ctx)
    ctx['latest_expansion_joined'] = 1
    ctx['pipeline'].append({'id': 'calc_latest_expansion', '$addFields': {
        'a_latest_date': {'$min': {'$map': {
            'input': '$a_sets.release_date', 'in': {'$toLong': '$$this'}
        }}}
    }})
    ctx['pipeline'].append({'id': 'get_latest_expansion', '$addFields': {
        'a_latest_set': {'$first': {'$filter': {
            'input': '$a_sets', 'cond': {'$eq': [{'$toLong': '$$this.release_date'}, '$a_latest_date']}
        }}}
    }})
    ctx['pipeline'].append({'id': 'remove_latest_expansion_id', '$unset': 'a_latest_set._id'})


def ensure_expansion_date(ctx: dict, exp: str) -> None:
    k = f'expansion_{exp}_calculated'
    if k in ctx:
        return
    ctx[k] = 1


def get_set_request(val: str, target: str = 'a_sets', allow_prelim: bool = True) -> SearchAnswer:
    if len(val) == 3 and allow_prelim:
        return {'sets': val.upper()}
    return {'$or': [{f'{target}.name': ireg(val)}, {f'{target}.code': val.upper()}]}, False


class SearchFunctionOrder(SearchFunction):
    @staticmethod
    def get_orders(tok: SearchToken) -> List[str]:
        known_orders: Dict[str, Union[str, List[str]]] = {
            'cmc-asc': ['mana_value~1'], 'mv-asc': 'cmc-asc', 'cmc-desc': ['mana_value~-1'], 'mv-desc': 'cmc-desc',
            'cmc': 'cmc-asc', 'mv': 'cmc-asc',
            'rarity': 'rarity-desc', 'rarity-asc': ['min_rarity_n~1'], 'rarity-desc': ['max_rarity_n~-1'],
            'color': 'color-asc', 'color-asc': ['color_order~1'], 'color-desc': ['color_order~-1'],
            'wr': 'wr-desc', 'wr-asc': ['a_playability.winrate~1'], 'wr-desc': ['a_playability.winrate~-1'],
            'winrate': 'wr-desc', 'winrate-asc': 'wr-asc', 'winrate-desc': 'wr-desc',
            'decks': 'decks-desc',
            'decks-asc': ['a_playability.deck_count~1'], 'decks-desc': ['a_playability.deck_count~-1']
        }
        if tok.value in known_orders:
            intermediate = known_orders[tok.value]
            if isinstance(intermediate, str):
                return cast(List[str], known_orders[intermediate])
            return intermediate
        raise SearchDataError(f'Unknown order: {tok.value}')

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        if 'wr' in tok.value or 'winrate' in tok.value or 'decks' in tok.value:
            ensure_playability_join(context)
        orders = self.get_orders(tok)
        for i in orders:
            context['sort'].append(i)
        return None


class SearchFunctionPlayability(SearchFunction):
    @staticmethod
    def get_target(tok: SearchToken) -> dict:
        if tok.comparator == '=':
            return tok.value

        arr = []
        if tok.value == 'played' or tok.value == 1:
            arr.append('playable')
            arr.append('staple')
            arr.append('good')
        if tok.value == 'staple' or tok.value == 'playable' or tok.value == 2:
            arr.append('good')
        if '=' in tok.comparator or tok.comparator == ':':
            arr.append(tok.value)
        return {'$in': arr}

    def process(self, tok: SearchToken, context: dict) -> Tuple[dict, bool]:
        return {'a_playability.playability': self.get_target(tok)}, False


class SearchFunctionSet(SearchFunction):
    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        if len(tok.value) == 3:
            return {'sets': tok.value.upper()}
        ensure_expansion_join(context)
        return get_set_request(tok.value)


class SearchFunctionFirstPrint(SearchFunction):
    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        ensure_latest_expansion(context)
        return get_set_request(tok.value, 'a_latest_set', False)


class SearchSyntaxCard(SearchSyntax):
    def __init__(self) -> None:
        super().__init__('cards', 'name', Card)
        self.add_filters()

    def parse_token(self, tok: SearchToken, context: dict, operator: str, invert: bool) -> Tuple[dict, dict]:
        face_search = False
        if tok.name[0] == '@':
            tok.name = tok.name[1:]
            face_search = True

        left, right = self.process_token(tok, context, operator, invert)
        if face_search:
            left = rename_query(left, lambda a: f'faces.{a}')
            right = rename_query(right, lambda a: f'faces.{a}')

        if tok.invert:
            left = {'$nor': [left]}
            right = {'$nor': [right]}
        return left, right

    def parse_group(self, data: SearchGroup, context: dict, deep_invert: bool = False,
                    invert: bool = False) -> Tuple[dict, dict]:
        left, right = super().parse_group(data, context, deep_invert, invert)
        if '@' not in data.modifiers:
            return left, right
        return {'faces': {'$elemMatch': left}}, {'faces': {'$elemMatch': right}}

    def add_filters(self) -> None:
        self.add_func('layout', SearchFunctionString('layout'),
                      'Search the card\'s layout.')
        self.add_func('color-identity', SearchFunctionColor('color_identity'),
                      'Search the card\'s color identity.', ['ci', 'id'])
        self.add_func('set', SearchFunctionSet(),
                      'Search the sets card appeared in.', ['e'])
        self.add_func('fprint', SearchFunctionFirstPrint(),
                      'Search the first set the card appeared in.', ['fp'])
        self.add_func('rarity', SearchFunctionExact('rarities')
                      .add_filter(SearchFilterFunction(get_rarity)),
                      'Search the rarities the card appeared in.', ['r'])
        self.add_func('category', SearchFunctionExact('categories')
                      .add_filter(SearchFilterLowercase())
                      .add_filter(SearchFilterCategory()),
                      'Search the categories the card has.',
                      ['cat', 'is', 'not', 'isnt'])
        self.add_func('format', SearchFunctionLegality(['legal', 'restricted']),
                      'Search the formats the card is legal or restricted in.', ['f'])
        self.add_func('legal', SearchFunctionLegality(['legal']),
                      'Search the formats the card is legal in.', ['l'])
        self.add_func('restricted', SearchFunctionLegality(['restricted']),
                      'Search the formats the card is restricted in.')
        self.add_func('banned', SearchFunctionLegality(['banned']),
                      'Search the formats the card is banned in.', ['ban'])
        self.add_func('not-legal', SearchFunctionLegality(['not legal']),
                      'Search the formats the card is not legal in.', ['nl'])
        self.add_func('max-count', SearchFunctionInt('max_count'),
                      'Search the card\'s maximum count.', ['mc'])
        self.add_func('name', SearchFunctionString('name'),
                      'Search the card\'s name.', ['n'])
        self.add_func('mana-value', SearchFunctionInt('mana_value'),
                      'Search the card\'s mana value.', ['mv', 'cmc'])
        self.add_func('oracle', SearchFunctionOracle(),
                      'Search the card\'s oracle text. Supports <code>~</code> and regular expressions.', ['o'])
        self.add_func('type', SearchFunctionString('types'),
                      'Search the card\'s type line.', ['t'])
        self.add_func('main-type', SearchFunctionExact('sets').add_filter(SearchFilterLowercase()),
                      'Search the main type of the card.', ['mt'])
        self.add_func('keyword', SearchFunctionExact('keywords').add_filter(SearchFilterLowercase()),
                      'Search the keywords the card has.', ['kw'])
        self.add_func('color', SearchFunctionColor('colors'),
                      'Search the colors the card has.', ['c'])
        self.add_func('cast-color', SearchFunctionColor('cast_colors'),
                      'Search the colored symbols in the card\'s casting cost.', ['cc', 'csc'])
        self.add_func('power', SearchFunctionInt('power'),
                      'Search the card\'s printed power.', ['pow'])
        self.add_func('toughness', SearchFunctionInt('toughness'),
                      'Search the card\'s printed toughness.', ['tou'])
        self.add_func('loyalty', SearchFunctionInt('loyalty'),
                      'Search the card\'s printed loyalty.', ['loy'])
        self.add_func('produces', SearchFunctionColor('produces').add_filter(SearchFilterProduces()),
                      'Search the colors this card could produce.', ['pro'])
        self.add_func('mana-cost', SearchFunctionManaCost().add_filter(SearchFilterFunction(get_mana_cost))
                      .add_filter(SearchFilterProduces()),
                      'Search the symbols in the card\'s mana cost.', ['mana'])
        self.add_func('order', SearchFunctionOrder().add_filter(SearchFilterLowercase()),
                      'Choose the order of the output results.', ['ord', 'sort'])
        self.add_func('play', SearchFunctionPlayability().add_filter(SearchFilterLowercase())
                      .add_filter(SearchFilterPlayabilityJoin()),
                      'Choose the playability of the card: 1/played, 2/playable/staple, 3/good.')
        self.add_func('wr', SearchFunctionFloat('a_playability.winrate')
                      .add_filter(SearchFilterPlayabilityJoin())
                      .add_transformer(SearchTransformerDelay()),
                      'Search the card\'s winrate.', ['winrate'])
        self.add_func('decks', SearchFunctionInt('a_playability.deck_count')
                      .add_filter(SearchFilterPlayabilityJoin())
                      .add_transformer(SearchTransformerDelay()),
                      'Search the number of decks the card was played in.', ['deck-count'])


class SearchFilterCategory(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        if tok.name == 'not' or tok.name == 'isnt':
            tok.invert = True
        return tok


class SearchFilterPlayabilityJoin(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        ensure_playability_join(context)
        return tok
