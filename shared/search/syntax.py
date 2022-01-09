from abc import ABC, abstractmethod
from logging import getLogger
from typing import Any, Dict, Generic, Iterable, List, Tuple, Type, TypeVar, Union, cast

from pymongo.database import Database
from pymongo.errors import OperationFailure
from pyparsing import ParseResults

from shared.helpers import configuration
from shared.helpers.exceptions import SearchDataError
from shared.search.renamer import (AggregationRenameController, OperatorControllerDict, OperatorControllerSingular,
                                   rename_expression, rename_field_name, rename_nothing, rename_query)
from shared.search.tokenizer import SearchGroup, SearchToken, tokenize_string
from shared.types.pseudotype import PseudoType

logger = getLogger('dreadrise.search')

SearchAnswer = Union[None, dict, Tuple[dict, bool], Tuple[dict, dict]]


class SearchFilter(ABC):
    @abstractmethod
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        pass


class SearchTransformer(ABC):
    @abstractmethod
    def invoke(self, item: SearchAnswer, context: dict) -> SearchAnswer:
        pass


class SearchFunction(ABC):
    filters: List[SearchFilter]
    transformers: List[SearchTransformer]

    def __init__(self) -> None:
        self.filters = []
        self.transformers = []

    @abstractmethod
    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        pass

    def postprocess(self, tok: SearchToken, context: dict) -> SearchAnswer:
        ans = self.process(tok, context)
        for i in self.transformers:
            ans = i.invoke(ans, context)
        return ans

    def add_filter(self, sf: SearchFilter) -> 'SearchFunction':
        self.filters.append(sf)
        return self

    def add_transformer(self, st: SearchTransformer) -> 'SearchFunction':
        self.transformers.append(st)
        return self

    def prepare(self, tok: SearchToken, context: dict) -> SearchToken:
        for i in self.filters:
            tok = i.invoke(tok, context)
        return tok


T = TypeVar('T', bound=PseudoType)


class SearchSyntax(Generic[T]):
    default: str = ''
    funcs: Dict[str, Tuple[SearchFunction, str, List[str], bool]]
    table_name: str
    model: Type[T]
    arc: AggregationRenameController

    def __init__(self, table_name: str, default: str, model: Type[T]):
        self.default = default
        self.funcs = {}
        self.default_object = {default: {'$exists': 1}}
        self.table_name = table_name
        self.model = model
        self.arc = AggregationRenameController()
        self.add_arc_methods()

    def add_arc_methods(self) -> None:
        self.arc.add_operator('addFields', OperatorControllerDict({'*': (rename_field_name, rename_expression)}))
        self.arc.add_operator('count', OperatorControllerSingular(rename_field_name))
        # not adding facet due to complexity
        self.arc.add_operator('group', OperatorControllerDict({
            '_id': (rename_nothing, rename_expression),
            '*': (rename_field_name, rename_expression)
        }))
        self.arc.add_operator('lookup', OperatorControllerDict({
            'localField': (rename_nothing, rename_field_name),
            'as': (rename_nothing, rename_field_name)
        }))
        self.arc.add_operator('match', OperatorControllerSingular(rename_query))
        self.arc.add_operator('project', OperatorControllerDict({'*': (rename_field_name, rename_expression)}))
        self.arc.add_operator('redact', OperatorControllerSingular(rename_expression))
        self.arc.add_operator('replaceRoot', OperatorControllerDict({'newRoot': (rename_nothing, rename_expression)}))
        self.arc.add_operator('replaceWith', OperatorControllerSingular(rename_expression))
        self.arc.add_operator('sort', OperatorControllerDict({'*': (rename_field_name, rename_nothing)}))
        self.arc.add_operator('sortByCount', OperatorControllerSingular(rename_expression))
        self.arc.add_operator('unset', OperatorControllerSingular(rename_field_name))
        self.arc.add_operator('unwind', OperatorControllerSingular(rename_expression))

    def add_func(self, name: str, func: SearchFunction, desc: str, aliases: List[str] = None) -> None:
        aliases = aliases or []
        self.funcs[name] = (func, desc, aliases, True)
        if aliases:
            for i in aliases:
                self.funcs[i] = (func, desc, [], False)

    def process_token(self, tok: SearchToken, context: dict, operator: str, invert: bool) -> Tuple[dict, dict]:
        if tok.name == 'default':
            tok.name = self.default
        if tok.name not in self.funcs:
            raise SearchDataError(f'Unknown operator: {tok.name}')
        func = self.funcs[tok.name][0]
        tok = func.prepare(tok, context)
        return self.obtain_token_tuple(func.postprocess(tok, context) or
                                       self.default_object, operator, invert != tok.invert)

    def obtain_token_tuple(self, x: SearchAnswer, operator: str, invert: bool) -> Tuple[dict, dict]:
        inverted_operator = operator if not invert else \
            ('n' if operator[0] == 'n' else '') + ('and' if 'and' not in operator else 'or')
        default_obj = self.default_object if 'and' in inverted_operator else {'aaaaa': {}}
        if not x:
            return default_obj, default_obj
        if isinstance(x, dict):
            return x, x
        if x[1] is True:
            return x[0], x[0]
        if isinstance(x[1], dict):
            return x
        return default_obj, x[0]

    def parse_token(self, tok: SearchToken, context: dict, operator: str, invert: bool) -> Tuple[dict, dict]:
        pre_aggregation, post_aggregation = self.process_token(tok, context, operator, invert)
        if tok.invert:
            pre_aggregation = {'$nor': [pre_aggregation]}
            post_aggregation = {'$nor': [post_aggregation]}
        return pre_aggregation, post_aggregation

    def join(self, operator: str, data: List[Dict[str, Any]]) -> dict:
        min_count = 1 if operator != 'or' else 2
        while len(data) < min_count:
            data.append(self.default_object if 'and' in operator else {'aaaaa': {}})
        if operator != 'nand':
            return {f'${operator}': data}
        else:  # looks like mongodb doesnt support nand
            return {'$nor': [{'$and': data}]}

    def parse_group(self, data: SearchGroup, context: dict, deep_invert: bool = False,
                    invert: bool = False) -> Tuple[dict, dict]:
        if invert:
            deep_invert = not deep_invert
        return self.parse_recursive(data.items, context, deep_invert, invert)

    def parse_recursive(self, data: Iterable[Union[SearchToken, SearchGroup, ParseResults]],
                        context: dict, deep_invert: bool = False, invert: bool = False) -> Tuple[dict, dict]:
        operators = [x.value for x in data if isinstance(x, SearchToken) and x.name == '_operator']
        operator_list = list(set(operators))
        if len(operator_list) > 1:
            ops = ', '.join(operator_list)
            raise SearchDataError(f'Too many operators in the same group: {ops}')
        inversion = 'n' if invert else ''
        operator = inversion + (operator_list[0] if len(operator_list) == 1 else 'and')

        non_operators = [x for x in data if not isinstance(x, SearchToken) or x.name != '_operator']

        arr = [self.parse_token(x, context, operator, deep_invert) if isinstance(x, SearchToken) else
               self.parse_group(x, context, deep_invert, x.negated) for x in non_operators]

        left_join = self.join(operator, [x[0] for x in arr])
        right_join = self.join(operator, [x[1] for x in arr])
        return left_join, right_join

    def parse(self, data: str, context: dict) -> Tuple[dict, dict]:
        results = tokenize_string(data)
        return self.parse_recursive(results, context)

    def create_pipeline(self, q: str, lim: int = 60, skip: int = 0) -> Tuple[List[Dict[str, Any]], List[Any], Any]:
        data = str(q).rstrip() if q else ''
        if not data:
            raise SearchDataError('Please provide one or more search operators.')

        context = {
            'pipeline': [],
            'limit': lim,
            'sort': [],
            'facets': {
                'count': [{'$count': 'count'}]
            }
        }
        query_left, query_right = self.parse(data, context)

        pipeline_ids = set()
        aggregation = [{'$match': query_left}]
        i: Dict[str, Any]
        for i in cast(List[Dict[str, Any]], context['pipeline']):
            if i['id'] not in pipeline_ids:
                pipeline_ids.add(i['id'])
                del i['id']
                aggregation.append(i)

        aggregation.append({'$match': query_right})
        build_sort = {}
        for j in cast(str, context['sort']):
            name, value = j.split('~')
            if name not in build_sort:
                build_sort[name] = int(value)
        build_sort[self.default] = 1
        build_sort['_id'] = 1

        limit_query: List[Dict[str, Any]] = [{'$sort': build_sort}]
        if cast(int, context['limit']) > -1:
            limit_query.append({'$skip': skip})
            limit_query.append({'$limit': context['limit']})

        facets = cast(Dict[str, List[Any]], context['facets'])
        facets['sample'] = limit_query
        aggregation.append({'$facet': facets})
        extra_facets = [x for x in facets if x not in ['sample', 'count']]
        return aggregation, extra_facets, (query_left, query_right)

    @staticmethod
    def remove_facets(pipeline: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        facets = []
        pipeline2 = []
        for i in pipeline:
            if '$facet' in i:
                facets.append(i)
            else:
                pipeline2.append(i)
        return pipeline2, facets

    def search(self, db: Database, q: str, lim: int = 60, s: int = 0) -> Tuple[int, List[T], Dict[str, Any]]:
        aggregation, extra_facets, debug_data = self.create_pipeline(q, lim, s)
        return self.search_with_pipeline(db, aggregation, extra_facets, debug_data)

    def search_with_pipeline(self, db: Database, agg: List[Dict[str, Any]], ef: List[Any], debug: Any) -> \
            Tuple[int, List[T], Dict[str, Any]]:
        try:
            allow_disk_use = bool(configuration.get('search_disk_use'))
            agg = list(db[self.table_name].aggregate(agg, allowDiskUse=allow_disk_use))
            matches = agg[0]['count'][0]['count'] if len(agg[0]['count']) > 0 else 0
            sample = agg[0]['sample'] if matches else []
            extra_dict = {x: agg[0][x] for x in ef}
            return matches, [self.model().load(x) for x in sample], extra_dict
        except OperationFailure as e:
            logger.debug(debug)
            logger.error(e)
            raise SearchDataError(e)


def format_func(x: str, y: Tuple[SearchFunction, str, List[str], bool]) -> str:
    if not y[3]:
        return ''
    if len(y[2]) == 0:
        return f'<code>{x}</code> - {y[1]}'
    join = ', '.join(y[2])
    return f'<code>{x} ({join})</code> - {y[1]}'
