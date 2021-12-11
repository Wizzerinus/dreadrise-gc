from datetime import datetime
from typing import Dict, List

from shared.card_enums import DeckPrivacy
from shared.types.pseudotype import PseudoType


class DeckGameRecord(PseudoType):
    opposing_deck_id: str = 'unknown'
    result: int = 0  # 0: tie, 1: win, -1: loss
    player_wins: int = 0
    player_losses: int = 0


class Deck(PseudoType):
    def pre_load(self, data: dict) -> None:
        super().pre_load(data)
        self.games = []
        for i in data['games']:
            cf = DeckGameRecord()
            cf.load(i)
            self.games.append(cf)

    def virtual_save(self) -> dict:
        dct = super().virtual_save()
        dct['games'] = [x.save() for x in self.games]
        return dct

    deck_id: str = 'unknown'
    name: str = 'Unknown'
    is_name_placeholder: bool = False
    author: str = 'Unknown Player'
    competition: str = ''
    format: str = 'Freeform'  # impossible to make this an enum due to database differences
    source: str = 'league'  # impossible to make this an enum due to database differences
    date: datetime

    tags: List[str] = []
    is_sorted: bool = False

    mainboard: Dict[str, int] = {}
    sideboard: Dict[str, int] = {}
    games: List[DeckGameRecord] = []
    wins: int = -1
    losses: int = 0
    ties: int = 0
    privacy: DeckPrivacy = 'public'

    assigned_rules: List[str] = []

    def process(self) -> None:
        if self.wins == -1:
            self.wins = len([x for x in self.games if x.result > 0])
            self.losses = len([x for x in self.games if x.result < 0])
            self.ties = len([x for x in self.games if x.result == 0])
            if not self.deck_id and self.competition:
                self.deck_id = self.competition + '--' + self.author
