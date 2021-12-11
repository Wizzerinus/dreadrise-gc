from typing import List

from shared.card_enums import popularity_multiplier
from shared.types.pseudotype import PseudoType


class Popularity(PseudoType):
    format: str
    card_name: str
    self_popularity: float
    total_popularity: float
    true_popularity: float

    def process(self) -> None:
        self.true_popularity = self.self_popularity - self.total_popularity * popularity_multiplier


class CompetitionPopularity(Popularity):
    competition: str


class DeckTagPopularity(Popularity):
    deck_tag: str


class FormatPopularity(Popularity):
    deck_count: int


class DeckTagCache(PseudoType):
    format: str
    tag: str
    tag_name: str
    cards: List[str]
    deck_count: int
    deck_wins: int
    deck_losses: int
    deck_winrate: float = 0

    def clean(self) -> None:
        if self.deck_wins + self.deck_losses > 0:
            self.deck_winrate = self.deck_wins / (self.deck_wins + self.deck_losses)


class CardPlayability(PseudoType):
    format: str
    card_name: str
    deck_count: int
    winrate: float
    playability: str  # impossible to make this an enum due to database differences
