from shared.card_enums import Archetype, Color
from shared.helpers.tagging.color import color_rule_applies
from shared.helpers.tagging.text import compile_rule, text_rule_applies
from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.pseudotype import PseudoType


class DeckTag(PseudoType):
    tag_id: str
    name: str
    description: str
    archetype: Archetype
    parents: list[str]


class DeckRule(PseudoType):
    tag_id: str
    rule_id: str
    priority: int = 0

    def applies_to(self, d: Deck, cards: dict[str, Card]) -> bool:
        return False


class TextDeckRule(DeckRule):
    text: str
    compiled: list | None = None

    def applies_to(self, d: Deck, cards: dict[str, Card]) -> bool:
        if not self.compiled:
            self.compiled = compile_rule(self.text)
        return text_rule_applies(d, self.compiled)


class ColorDeckRule(DeckRule):
    colors: list[Color]

    def applies_to(self, d: Deck, cards: dict[str, Card]) -> bool:
        return color_rule_applies(d, cards, set(self.colors))
