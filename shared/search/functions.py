from abc import abstractmethod
from typing import Any, Callable, List, Optional

import arrow

from shared.helpers.exceptions import SearchDataError, SearchSyntaxError
from shared.helpers.magic import get_color_combination
from shared.helpers.util import ireg
from shared.search.syntax import SearchAnswer, SearchFilter, SearchFunction, SearchTransformer
from shared.search.tokenizer import SearchToken


class SearchFunctionExact(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        return {self.name: {'$eq': tok.value}}


class SearchFunctionArray(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        return {self.name: {'$in': tok.value}}


class SearchFunctionDict(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        return {f'{self.name}.{tok.value}': {'$exists': 1}}


class SearchFunctionString(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        val = tok.value if tok.comparator != '=' else f'^{tok.value}$'
        return {self.name: ireg(val)}


class SearchFunctionInt(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        try:
            num = int(tok.value)
        except ValueError:
            raise SearchDataError(f'Unable to parse number: {tok.value}')

        cmps = {'=': '$eq', '>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte', ':': '$eq'}
        return {self.name: {cmps[tok.comparator]: num}}


class SearchFunctionFloat(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        try:
            num = float(tok.value)
        except ValueError:
            raise SearchDataError(f'Unable to parse number: {tok.value}')

        cmps = {'=': '$eq', '>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte', ':': '$eq'}
        return {self.name: {cmps[tok.comparator]: num}}


class SearchFunctionArrayValidator(SearchFunction):
    def __init__(self, targets: List[str]):
        super().__init__()
        self.targets = targets

    @abstractmethod
    def greater_or_equal(self, target: str, tok: SearchToken) -> dict:
        pass

    @abstractmethod
    def greater(self, target: str, tok: SearchToken) -> dict:
        pass

    @abstractmethod
    def exists(self, target: str, tok: SearchToken) -> dict:
        pass

    @abstractmethod
    def contains(self, target: str, tok: SearchToken) -> bool:
        pass

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        all_required_greater_or_equal: List[dict] = []
        some_required_greater: List[dict] = []
        some_reverse_exists: List[dict] = []

        for i in self.targets:
            if self.contains(i, tok):
                all_required_greater_or_equal.append(self.greater_or_equal(i, tok))
                some_required_greater.append(self.greater(i, tok))
            else:
                some_reverse_exists.append(self.exists(i, tok))

        if tok.comparator == '<=' or tok.comparator == ':':
            return {'$nor': some_required_greater + some_reverse_exists}
        if tok.comparator == '=':
            return {'$and': all_required_greater_or_equal + [{'$nor': some_required_greater + some_reverse_exists}]}
        if tok.comparator == '>':
            return {'$and': all_required_greater_or_equal + [{'$or': some_required_greater + some_reverse_exists}]}
        if tok.comparator == '<':
            return {'$nor': some_required_greater + some_reverse_exists + [{'$and': all_required_greater_or_equal}]}
        return {'$and': all_required_greater_or_equal}


class SearchFunctionBitmap(SearchFunctionArrayValidator):
    def __init__(self, name: str, targets: List[str]):
        super().__init__(targets)
        self.name = name

    def greater_or_equal(self, target: str, tok: SearchToken) -> dict:
        return {self.name: target}

    def greater(self, target: str, tok: SearchToken) -> dict:
        return {'aaaaa': -1}

    def exists(self, target: str, tok: SearchToken) -> dict:
        return {self.name: target}

    def contains(self, target: str, tok: SearchToken) -> bool:
        return target in tok.value


class SearchFunctionZeroList(SearchFunctionArrayValidator):
    def __init__(self, name: str, targets: List[str]):
        super().__init__(targets)
        self.name = name

    def greater_or_equal(self, target: str, tok: SearchToken) -> dict:
        return {f'{self.name}.{target}': {'$gt': 0}}

    def greater(self, target: str, tok: SearchToken) -> dict:
        return {'aaaaa': -1}

    def exists(self, target: str, tok: SearchToken) -> dict:
        return {f'{self.name}.{target}': {'$gt': 0}}

    def contains(self, target: str, tok: SearchToken) -> bool:
        return target in tok.value


class SearchFilterUppercase(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        tok.value = tok.value.upper()
        return tok


class SearchFilterLowercase(SearchFilter):
    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        tok.value = tok.value.lower()
        return tok


class SearchFilterFunction(SearchFilter):
    def __init__(self, f: Callable[[Any], Any]):
        self.func = f

    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        tok.value = self.func(tok.value)
        return tok


class SearchFilterComprehension(SearchFilter):
    def __init__(self, f: Callable[[Any], Any]):
        self.func = f

    def invoke(self, tok: SearchToken, context: dict) -> SearchToken:
        tok.value = [self.func(x) for x in tok.value]
        return tok


class SearchTransformerDelay(SearchTransformer):
    def invoke(self, item: SearchAnswer, context: dict) -> SearchAnswer:
        if not item:
            return item
        if isinstance(item, dict):
            return item, False
        if isinstance(item[1], bool):
            return item[0], False
        raise SearchSyntaxError('Delaying double-mode functions isn\'t supported')


class SearchFunctionColor(SearchFunction):
    def __init__(self, name: str, targets: List[str] = None, using_zerolist: bool = False):
        super().__init__()
        if not targets:
            targets = ['white', 'blue', 'black', 'red', 'green'] if not using_zerolist else ['0', '1', '2', '3', '4']
        self.name = name
        self.nums = SearchFunctionInt(f'{name}_len')

        # bitmap needs the token value to be an array.
        # so we make it an array.
        # 'wub' -> ['white', 'blue', 'black'] <- 'esper'
        constructor = SearchFunctionBitmap if not using_zerolist else SearchFunctionZeroList
        self.bms = constructor(name, targets)\
            .add_filter(SearchFilterLowercase())\
            .add_filter(SearchFilterFunction(get_color_combination))

    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        try:
            return self.nums.process(tok, context)
        except SearchDataError:
            tok = self.bms.prepare(tok, context)
            return self.bms.process(tok, context)


class SearchFunctionDate(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> SearchAnswer:
        try:
            time = arrow.get(tok.value)
        except arrow.ParserError:
            try:
                time = arrow.utcnow().dehumanize(tok.value)
            except ValueError:
                raise SearchDataError(f'Unable to parse date: {tok.value}')

        cmps = {'=': '$eq', '>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte', ':': '$eq'}
        return {self.name: {cmps[tok.comparator]: time.datetime}}


class SearchFunctionStringArray(SearchFunction):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def process(self, tok: SearchToken, context: dict) -> Optional[dict]:
        val = tok.value if tok.comparator != '=' else f'^{tok.value}$'
        return {self.name: {'$elemMatch': ireg(val)}}
