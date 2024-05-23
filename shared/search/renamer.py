from abc import ABC, abstractmethod
from typing import Any, Callable

RenameMethod = Callable[[Any, Callable[[str], str]], Any]


class OperatorController(ABC):
    @abstractmethod
    def rename(self, value: Any, renamer: Callable[[str], str]) -> Any:
        pass


def rename_nothing(value: Any, renamer: Callable[[str], str]) -> Any:
    return value


def rename_field_name(value: Any, renamer: Callable[[str], str]) -> Any:
    return renamer(str(value))


def rename_expression(value: Any, renamer: Callable[[str], str]) -> Any:
    """
        Expressions can include field paths, literals, system variables, expression objects, and expression operators.
        Expressions can be nested.
        Field path: Field name prepended with $.
        Literal: Anything without a $.
        System Variable: Anything prepended with $$.
        Expression Object: dict[Field, Expression]
        Expression Operator: singleItemdict[operatorname, argument] operatorname starts with $
    """
    # Oh yeah I have no idea whether rename_expression != rename_query
    if isinstance(value, str):
        if value[0:1] == '$$' or value[0] != '$':
            return value
        return '$' + rename_field_name(value[1:], renamer)
    elif isinstance(value, dict):
        ans = {}
        for k, v in value.items():
            if k[0] == '$':
                # K is an operator, V is an argument
                ans[k] = rename_expression(v, renamer)
            else:
                # K is a field, V is an expression
                ans[rename_field_name(k, renamer)] = rename_expression(v, renamer)
        return ans
    elif isinstance(value, list):
        return [rename_expression(u, renamer) for u in value]
    return value


def rename_query(value: Any, renamer: Callable[[str], str]) -> Any:
    ans = {}
    if not isinstance(value, dict):
        return value
    for i, j in value.items():
        if i[0] == '$' and isinstance(j, list):
            ans[i] = [rename_query(x, renamer) for x in j]
        elif i == '$elemMatch':  # AAAAAAA
            ans[i] = j
        elif i[0] == '$':
            ans[i] = rename_query(j, renamer)
        elif isinstance(j, list):
            ans[renamer(i)] = [rename_query(x, renamer) for x in j]
        else:
            ans[renamer(i)] = rename_query(j, renamer)
    return ans


class OperatorControllerSingular(OperatorController):
    def __init__(self, method: RenameMethod):
        self.method = method

    def rename(self, value: Any, renamer: Callable[[str], str]) -> Any:
        return self.method(value, renamer)


class OperatorControllerDict(OperatorController):
    def __init__(self, signature: dict[str, tuple[RenameMethod, RenameMethod]]):
        # First method is for the name, second for the value
        self.signature = signature

    def rename(self, value: Any, renamer: Callable[[str], str]) -> Any:
        if not isinstance(value, dict):
            return value
        ans = {}
        for i, j in value.items():
            if i in self.signature:
                sgn = self.signature[i]
            elif '*' in self.signature:
                sgn = self.signature['*']
            else:
                sgn = (rename_nothing, rename_nothing)
            ans[sgn[0](i, renamer)] = sgn[1](j, renamer)
        return ans


class AggregationRenameController:
    operators: dict[str, OperatorController]

    def __init__(self) -> None:
        self.operators = {}

    def add_operator(self, name: str, oc: OperatorController) -> None:
        self.operators['$' + name] = oc

    def rename_pipeline(self, pipeline: list[dict[str, Any]], renamer: Callable[[str], str]) -> list[dict[str, Any]]:
        result = []
        for i in pipeline:
            if not i:
                continue

            key, value = list(i.items())[0]
            if key not in self.operators:
                result.append({key: value})
            else:
                result.append({key: self.operators[key].rename(value, renamer)})

        return result
