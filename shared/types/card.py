import re

from shared.card_enums import (CardType, Color, Legality, ManaDict, ManaType, Rarity, basics, card_types, color_order,
                               color_symbols_single, color_symbols_to_colors, mana_types, rarities)
from shared.helpers.exceptions import RisingDataError
from shared.helpers.magic import process_mana_cost_text, process_oracle
from shared.helpers.util import clean_name, sum_mana_costs
from shared.types.pseudotype import PseudoType


class CardFace(PseudoType):
    name: str
    mana_cost: ManaDict
    mana_cost_str: str
    mana_value: int
    oracle: str
    t_oracle: str
    types: str
    main_type: CardType

    colors: list[Color]
    colors_len: int
    cast_colors: list[Color]
    cast_colors_len: int

    power: int | None = 0
    toughness: int | None = 0
    loyalty: int | None = 0

    image: str
    produces: list[ManaType]
    produces_len: int

    def process_produces(self) -> None:
        produces_set: set[ManaType] = set()
        if 'Land' in self.types:
            for k, v in basics.items():
                if k in self.types:
                    produces_set.add(v)

        for i, j in zip(color_symbols_single, mana_types):
            regex_color_produce = re.compile(fr'add\b.*{{{i}}}', re.I)
            if regex_color_produce.search(self.oracle):
                produces_set.add(j)

        regex_rainbow = re.compile(r'\badd\b.*\b(of any color|any combination of colors|any one color|'
                                   r'one mana of that color|different colors|any of the)\b', re.I)
        regex_sylvan_scrying = re.compile(r'search.*\bland]? card', re.I)
        regex_farseek = re.compile(r'search.*\b(forest|island|swamp|plains|mountain) card', re.I)
        regex_shifting_land = re.compile(r'choose.*basic land.*create.*land', re.I)
        regex_treasure = re.compile(r'create.*\b(gold|treasure).*\btoken', re.I)
        if regex_rainbow.search(self.oracle) or regex_treasure.search(self.oracle) or \
                (regex_sylvan_scrying.search(self.oracle) and 'other than a' not in self.oracle) or \
                (regex_farseek.search(self.oracle) and 'basic' not in self.oracle) or \
                regex_shifting_land.search(self.oracle) or \
                ('Choose a color' in self.oracle and ('add' in self.oracle or 'Add' in self.oracle)):
            for k, v in basics.items():
                produces_set.add(v)

        for k, v in basics.items():
            regex_field_trip = re.compile(rf'search.*\bbasic {k} card', re.I)
            regex_tend_to_the_grove = re.compile(rf'create.*{k}.*card', re.I)
            if regex_field_trip.search(self.oracle) or regex_tend_to_the_grove.search(self.oracle):
                produces_set.add(v)

        if len(produces_set) > 0 and 'Snow' in self.types:
            produces_set.add('snow')
        self.produces = list(produces_set)
        self.produces_len = len(self.produces)

    def process(self) -> None:
        for i in card_types:
            if i == 'tribal':
                raise RisingDataError(f'Invalid card type (affected card: {self.name}).')
            if i.title() in self.types:
                self.main_type = i
                break

        self.t_oracle = self.oracle.replace(self.name, '~')
        if 'Legendary' in self.types and ', ' in self.name:
            stripped_name = self.name.split(', ')[0]
            self.t_oracle = self.t_oracle.replace(stripped_name, '~')

        self.colors_len = len(self.colors)
        self.cast_colors_len = len(self.cast_colors)

        self.process_produces()


class Card(PseudoType):
    def pre_load(self, data: dict) -> None:
        super().pre_load(data)
        self.faces = []
        for i in data['faces']:
            self.faces.append(CardFace().load(i))

    def virtual_save(self) -> dict:
        dct = super().virtual_save()
        dct['faces'] = [x.save() for x in self.faces]
        if 'fixed_faces' in dct:
            dct['fixed_faces'] = [x.save() for x in self.fixed_faces]
        return dct

    def __init__(self) -> None:
        self.max_count = 4

    def name_join(self) -> bool:
        """Returns whether the name of the card should include names of each face (true), or only one (false)."""
        return self.layout == 'split'

    def mana_join(self) -> bool:
        """Returns whether the mana cost of the card should include costs of each face (true), or only one (false)."""
        return self.layout == 'split'

    def type_join(self) -> bool:
        """Returns whether the type of the card should include types of each face (true), or only one (false)."""
        return self.layout in ['split', 'modal_dfc', 'adventure']

    def image_join(self) -> bool:
        """Returns whether the card has two images (true), or only one (false)."""
        return self.layout in ['modal_dfc', 'transform']

    def cast_join(self) -> bool:
        """Returns whether both halves of the card can be cast (true), or only one (false). Used for Karsten module."""
        return self.layout in ['split', 'adventure', 'modal_dfc']

    def get_name_from_faces(self) -> str:
        return ' // '.join([x.name for x in self.faces]) if self.name_join() else self.faces[0].name

    faces: list[CardFace]
    layout: str  # impossible to make this an enum due to database differences
    color_identity: list[Color]
    color_identity_len: int

    sets: list[str]
    rarities: list[Rarity]
    min_rarity: Rarity
    max_rarity: Rarity
    min_rarity_n: int
    max_rarity_n: int
    categories: list[str]  # impossible to make this an enum due to database differences
    legality: dict[str, Legality]
    max_count: int

    name: str
    card_id: str
    mana_cost: ManaDict
    mana_cost_str: str
    mana_value: int
    oracle: str
    t_oracle: str
    types: str
    main_type: CardType
    keywords: list[str] = []

    colors: list[Color]
    colors_len: int
    cast_colors: list[Color]
    cast_colors_len: int
    color_order: int

    power: int | None = 0
    toughness: int | None = 0
    loyalty: int | None = 0

    image: str
    produces: list[ManaType]
    produces_len: int

    singular_name: str
    fixed_faces: list[CardFace]
    processed_oracle: str
    processed_mana_cost: str

    def post_load(self) -> None:
        self.fixed_faces = self.faces if self.image_join() else [self.faces[0]]
        singular_names = self.faces if self.name_join() else [self.faces[0]]
        self.singular_name = ' // '.join([a.name for a in singular_names])
        self.processed_oracle = process_oracle(self.oracle)
        self.processed_mana_cost = process_mana_cost_text(self.oracle)

    def process(self) -> None:
        try:
            del self.fixed_faces
            del self.singular_name
        except AttributeError:
            pass

        self.name = self.get_name_from_faces()
        if len(self.faces) < 1 or len(self.faces) > 2:
            raise RisingDataError(f'Invalid number of faces (affected card: {self.name}).')

        if len({x.name for x in self.faces}) != len(self.faces):
            raise RisingDataError(f'Name is repeated among faces: {self.name}')

        for i in self.faces:
            i.process()

        self.card_id = clean_name(self.name)

        if self.mana_join():
            self.mana_cost = sum_mana_costs([x.mana_cost for x in self.faces])
            self.mana_cost_str = ' // '.join([x.mana_cost_str for x in self.faces])
            self.mana_value = sum([x.mana_value for x in self.faces])
            self.colors = list(set(sum([x.colors for x in self.faces], [])))
        else:
            self.mana_cost = self.faces[0].mana_cost
            self.mana_cost_str = self.faces[0].mana_cost_str
            self.mana_value = self.faces[0].mana_value
            self.colors = self.faces[0].colors

        self.oracle = '\n\n\n'.join([x.oracle for x in self.faces])
        self.t_oracle = '\n\n\n'.join([x.t_oracle for x in self.faces])

        if self.type_join():
            self.types = ' // '.join([x.types for x in self.faces])
        else:
            self.types = self.faces[0].types

        self.main_type = self.faces[0].main_type

        self.colors_len = len(self.colors)
        self.cast_colors = list(set(sum([x.cast_colors for x in self.faces], [])))
        self.cast_colors_len = len(self.cast_colors)
        self.produces = list(set(sum([x.produces for x in self.faces], [])))
        self.produces_len = len(self.produces)

        if hasattr(self.faces[0], 'power'):
            self.power = self.faces[0].power
        if hasattr(self.faces[0], 'toughness'):
            self.toughness = self.faces[0].toughness
        if hasattr(self.faces[0], 'loyalty'):
            self.loyalty = self.faces[0].loyalty
        self.image = self.faces[0].image

        self.color_identity_len = len(self.color_identity)

        has_max_rarity = False
        for r, n in zip(rarities, range(5, -1, -1)):
            if r in self.rarities:
                self.min_rarity = r
                self.min_rarity_n = n

                if not has_max_rarity:
                    has_max_rarity = True
                    self.max_rarity = r
                    self.max_rarity_n = n

        if len(self.colors) == 0:
            self.color_order = 31
        else:
            color_set = set(self.colors)
            for cc, n in zip(color_order, range(32)):
                if {color_symbols_to_colors[x] for x in cc} == color_set:
                    self.color_order = n

        if 'Basic' in self.types or 'deck can have any number of cards named ~' in self.t_oracle:
            self.max_count = 1000

    def get_sideboard_importance(self, count: int) -> int:
        return 3 if 'first-mate' in self.categories or 'companion' in self.categories else 0
