from shared.types.pseudotype import PseudoType


class FormatCache(PseudoType):
    format: str = 'unknown'
    legal: set[str] = set()
    restricted: set[str] = set()
    banned: set[str] = set()

    def pre_load(self, data: dict) -> None:
        self.format = data['format']
        self.legal = set(data['legal'])
        self.restricted = set(data['restricted'])
        self.banned = set(data['banned'])
