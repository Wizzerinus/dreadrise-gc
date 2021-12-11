from typing import Set

from shared.types.pseudotype import PseudoType


class FormatCache(PseudoType):
    format: str = 'unknown'
    legal: Set[str] = set()
    restricted: Set[str] = set()
    banned: Set[str] = set()

    def pre_load(self, data: dict) -> None:
        self.format = data['format']
        self.legal = set(data['legal'])
        self.restricted = set(data['restricted'])
        self.banned = set(data['banned'])
