from datetime import datetime

from shared.helpers.util import clean_name
from shared.types.pseudotype import PseudoType


class Competition(PseudoType):
    competition_id: str
    name: str
    format: str  # impossible to make this an enum due to database differences
    date: datetime
    type: str  # impossible to make this an enum due to database differences

    def process(self) -> None:
        if not self.competition_id:
            self.competition_id = clean_name(self.name)
