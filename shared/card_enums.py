from typing import Literal, get_args

Color = Literal['white', 'blue', 'black', 'red', 'green']
colors: tuple[Color, ...] = get_args(Color)
colors_single = ['W', 'U', 'B', 'R', 'G']
colors_double = ['WU', 'UB', 'BR', 'RG', 'GW', 'WB', 'UR', 'BG', 'RW', 'GU']
colors_triple = ['WUB', 'UBR', 'BRG', 'RGW', 'GWU', 'WUR', 'UBG', 'BRW', 'RGU', 'GWB']
colors_quad = ['WUBR', 'UBRG', 'BRGW', 'RGWU', 'GWUB']
colors_special = ['WUBRG', '']
color_order = colors_single + colors_double + colors_triple + colors_quad + colors_special
color_symbols_to_colors: dict[str, Color] = dict(zip(colors_single, colors))

ManaType = Literal['white', 'blue', 'black', 'red', 'green', 'colorless', 'snow']
mana_types: tuple[ManaType, ...] = get_args(ManaType)
color_symbols_single = ['W', 'U', 'B', 'R', 'G', 'C', 'S']
color_symbols_to_mana_types: dict[str, ManaType] = dict(zip(color_symbols_single, mana_types))

ManaSymbol = Literal['white', 'blue', 'black', 'red', 'green', 'colorless', 'snow', 'any',
                     'pwhite', 'pblue', 'pblack', 'pred', 'pgreen',
                     'cwhite', 'cblue', 'cblack', 'cred', 'cgreen',
                     'white/blue', 'blue/black', 'black/red', 'red/green', 'green/white',
                     'white/black', 'blue/red', 'black/green', 'red/white', 'green/blue',
                     '2/white', '2/blue', '2/black', '2/red', '2/green',
                     'tap', 'untap', 'zero', 'x', 'prismatic',
                     'pwhite/blue', 'pblue/black', 'pblack/red', 'pred/green', 'pgreen/white',
                     'pwhite/black', 'pblue/red', 'pblack/green', 'pred/white', 'pgreen/blue']
mana_symbols: tuple[ManaSymbol, ...] = get_args(ManaSymbol)

MiscellanousSymbol = Literal['X', 'S', 'V', 'C']
misc_symbols: tuple[MiscellanousSymbol, ...] = get_args(MiscellanousSymbol)
misc_mana_symbols: tuple[ManaSymbol, ...] = ('x', 'snow', 'prismatic', 'colorless')
misc_to_mana_symbols: dict[str, ManaSymbol] = dict(zip(misc_symbols, misc_mana_symbols))

basics: dict[str, Color] = {'Plains': 'white', 'Island': 'blue', 'Swamp': 'black', 'Mountain': 'red', 'Forest': 'green'}

CardType = Literal[
    'land', 'creature', 'planeswalker', 'artifact', 'enchantment', 'instant', 'sorcery', 'battle', 'tribal'
]
card_types: tuple[CardType, ...] = get_args(CardType)

Rarity = Literal['special', 'mythic', 'rare', 'uncommon', 'common', 'basic']
rarities: tuple[Rarity, ...] = get_args(Rarity)
rarity_map: dict[str, Rarity] = {
    'c': 'common',
    'u': 'uncommon',
    'r': 'rare',
    'm': 'mythic', 'mythic-rare': 'mythic', 'mythic rare': 'mythic',
    's': 'special', 'bonus': 'special',
    'l': 'basic', 'land': 'basic', 'b': 'basic', 'basic land': 'basic'
}

Legality = Literal['legal', 'restricted', 'not_legal', 'banned']
legalities: tuple[Legality, ...] = get_args(Legality)

ManaDict = dict[ManaSymbol, int]

DeckPrivacy = Literal['public', 'unlisted', 'private']
deck_privacy_options: tuple[DeckPrivacy, ...] = get_args(DeckPrivacy)

Archetype = Literal['aggro', 'midrange', 'control', 'combo', 'ramp',
                    'aggro-control', 'combo-control', 'aggro-combo', 'tempo', 'unclassified']
archetypes: tuple[Archetype, ...] = get_args(Archetype)

color_combo_localization: dict[str, tuple[Color, ...]] = {
    'azorius': ('white', 'blue'), 'dimir': ('blue', 'black'), 'rakdos': ('black', 'red'), 'gruul': ('red', 'green'),
    'selesnya': ('green', 'white'),
    'orzhov': ('white', 'black'), 'izzet': ('blue', 'red'), 'golgari': ('black', 'green'), 'boros': ('red', 'white'),
    'simic': ('green', 'blue'),
    'esper': ('white', 'blue', 'black'), 'grixis': ('blue', 'black', 'red'), 'jund': ('black', 'red', 'green'),
    'naya': ('red', 'green', 'white'), 'bant': ('green', 'white', 'blue'),
    'abzan': ('white', 'black', 'green'), 'jeskai': ('blue', 'red', 'white'), 'sultai': ('black', 'green', 'blue'),
    'mardu': ('red', 'white', 'black'), 'temur': ('green', 'blue', 'red'),
    'indatha': ('white', 'black', 'green'), 'raugrin': ('blue', 'red', 'white'), 'zagoth': ('black', 'green', 'blue'),
    'savai': ('red', 'white', 'black'), 'ketria': ('green', 'blue', 'red')
}

popularity_multiplier = 0.8
format_popularity = 1.35
