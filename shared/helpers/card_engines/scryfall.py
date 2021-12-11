import re
from typing import List, cast

from shared.card_enums import color_symbols_to_colors, colors_single
from shared.helpers.magic import calculate_mana_value, get_rarity, process_mana_cost_dict
from shared.helpers.util import int_def
from shared.types.card import Card, CardFace
from shared.types.format_cache import FormatCache


def get(key: str, d: dict, d2: dict) -> str:
    return cast(str, d[key] if key in d else d2[key])


def get_number(s: str) -> int:
    number_regex = re.compile(r'(\d)+')
    try:
        match = number_regex.match(s)
        return int(match.group(1)) if match else 0
    except TypeError:
        return int_def(s)


def build_card_face(d1: dict, d2: dict) -> CardFace:
    cf = CardFace()
    cf.name = get('name', d1, d2)
    cf.mana_cost_str = get('mana_cost', d1, d2)
    cf.mana_cost = process_mana_cost_dict(cf.mana_cost_str)
    cf.mana_value = calculate_mana_value(cf.mana_cost)
    cf.oracle = get('oracle_text', d1, d2)
    cf.types = get('type_line', d1, d2)
    card_colors = cast(list, d1['colors'] if 'colors' in d1 else d2['colors'])
    cf.colors = [color_symbols_to_colors[x] for x in card_colors]
    cf.cast_colors = list({color_symbols_to_colors[x] for x in cf.mana_cost if x in colors_single})

    if 'Creature' in cf.types:
        cf.power = get_number(get('power', d1, d2))
        cf.toughness = get_number(get('toughness', d1, d2))

    if 'Planeswalker' in cf.types:
        try:
            cf.loyalty = get_number(get('loyalty', d1, d2))
        except KeyError:  # Garruk, Veil-Cursed
            cf.loyalty = 0

    uris = cast(dict, get('image_uris', d1, d2))
    cf.image = uris['normal']
    return cf


def build_card(i: dict, formats: List[str], fcs: List[FormatCache]) -> Card:
    c = Card()
    c.layout = i['layout'].lower()
    if 'card_faces' in i:
        c.faces = [build_card_face(j, i) for j in i['card_faces']]
    else:
        c.faces = [build_card_face(i, i)]
    name = c.get_name_from_faces()
    c.color_identity = list({color_symbols_to_colors[x] for x in i['color_identity']})
    c.sets = [i['set'].upper()]
    c.keywords = [x.lower() for x in i['keywords']]
    c.rarities = [get_rarity(i['rarity'])]
    c.categories = []

    c.legality = {x: y for x, y in i['legalities'].items() if x in formats}
    for fc in fcs:
        if name in fc.banned:
            c.legality[fc.format] = 'banned'
        elif name in fc.restricted:
            c.legality[fc.format] = 'restricted'
        elif name in fc.legal:
            c.legality[fc.format] = 'legal'
        else:
            c.legality[fc.format] = 'not_legal'
    c.max_count = 4

    return c
