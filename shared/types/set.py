from datetime import datetime

from shared.types.pseudotype import PseudoType


class Expansion(PseudoType):
    code: str
    name: str
    release_date: datetime
