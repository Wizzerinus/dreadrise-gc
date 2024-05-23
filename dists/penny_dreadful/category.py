import re

from shared.types.card import Card


def _is_typed(c: str) -> bool:
    return 'Island' in c or 'Plains' in c or 'Forest' in c or 'Swamp' in c or 'Mountain' in c


def add_card_categories(c: Card) -> list[str]:
    """
    Add card categories to a card object inplace.
    :param c: the card to modify
    :return: nothing
    """
    categories = []

    first_type = c.faces[0].types
    first_oracle = c.faces[0].oracle.split('\n')
    power = ['Ancestral Recall', 'Time Walk', 'Timetwister', 'Black Lotus',
             'Mox Pearl', 'Mox Sapphire', 'Mox Jet', 'Mox Ruby', 'Mox Emerald']
    pow2 = ['Mana Crypt', 'Sol Ring', 'Time Vault', 'Strip Mine', 'Tinker', 'Library of Alexandria']
    permanent_types = ['Land', 'Creature', 'Artifact', 'Enchantment', 'Planeswalker']
    historic_types = ['Artifact', 'Saga', 'Legendary']

    if c.name in power:
        categories.append('power')
    if c.name in power or c.name in pow2:
        categories.append('power2')
    if [x for x in c.faces if 'Land' not in x.types]:
        categories.append('spell')
    if [x for x in permanent_types if x in c.types]:
        categories.append('permanent')
    if [x for x in historic_types if x in first_type]:
        categories.append('historic')

    true_duals = ['Badlands', 'Bayou', 'Plateau', 'Savannah', 'Scrubland', 'Tundra',
                  'Tropical Island', 'Volcanic Island', 'Tundra', 'Underground Sea']
    slow_fetches = ['Bad River', 'Flood Plain', 'Grasslands', 'Mountain Valley', 'Rocky Tar Pit',
                    'Evolving Wilds', 'Terramorphic Expanse', 'Fabled Passage']
    filters = ['Mystic Gate', 'Sunken Ruins', 'Graven Cairns', 'Fire-Lit Thicket', 'Wooded Bastion',
               'Skycloud Expanse', 'Darkwater Catacombs', 'Shadowbrood Ridge', 'Mossfire Valley', 'Sungrass Prairie',
               'Fetid Heath', 'Twilight Mire', 'Flooded Grove', 'Cascade Bluffs', 'Rugged Prairie',
               'Crystal Quarry', 'Cascading Cataracts']
    trilands = ['Arcane Sanctum', 'Crumbling Necropolis', 'Savage Lands', 'Jungle Shrine', 'Seaside Citadel',
                'Mystic Monastery', 'Opulent Palace', 'Nomad Outpost', 'Frontier Bivouac', 'Sandsteppe Citadel']
    if c.main_type == 'land':
        if c.produces_len == 2 and 'cycling' in c.keywords:
            categories.append('bicycle')
        if re.compile('return a.*you control to its owner\'s hand').search(c.oracle):
            categories.append('bounceland')
        if c.produces_len == 2 and '{1}, {T}, Sacrifice ~: Draw a card' in c.t_oracle:
            categories.append('canopyland')
        if '~ enters the battlefield tapped unless you control a' in c.t_oracle:
            categories.append('checkland')
        if c.name in true_duals:
            categories.append('true-dual')
        if c.produces_len == 2 and 'fewer other lands' in c.t_oracle:
            categories.append('fastland')
        if '{T}, Pay 1 life, Sacrifice ~:' in c.t_oracle:
            categories.append('fetchland')
        if c.name in slow_fetches:
            categories.append('slowfetch')
        if c.name in filters:
            categories.append('filterland')
        if 'When ~ enters the battlefield, you gain' in c.t_oracle:
            categories.append('gainland')
        if 'As ~ enters the battlefield, you may reveal' in c.t_oracle:
            categories.append('reveal-land')
        if c.produces_len == 3 and 'tapped' not in c.oracle and '~ deals 1 damage to you' in c.t_oracle:
            categories.append('painland')
        if c.produces_len == 2 and 'When ~ enters the battlefield, scry' in c.t_oracle:
            categories.append('scryland')
        if 'As ~ enters the battlefield, you may pay 2 life' in c.t_oracle:
            categories.append('shockland')
        if 'storage counter' in c.oracle:
            categories.append('storageland')
        if re.compile('(~|it) become(s?) a.*creature').search(c.t_oracle):
            categories.append('manland')
        if c.name in trilands:
            categories.append('triland')
        if 'Triome' in c.name:
            categories.append('tricycle')
        if '~ enters the battlefield tapped unless you control two or more basic' in c.t_oracle:
            categories.append('tangoland')
        if '~ enters the battlefield tapped unless you control two or more lands' in c.t_oracle:
            categories.append('slowland')
        if _is_typed(c.types):
            categories.append('fetchable')

    # foretell is a special action, dash is an alternate cost so removing them
    activated_keywords = ['equip', 'cycling', 'transfigure', 'unearth', 'levelup', 'outlast', 'crew',
                          'ninjutsu', 'commanderninjutsu', 'transmute', 'forecast', 'auraswap', 'reinforce',
                          'scavenge', 'embalm', 'eternalize', 'fortify', 'adapt', 'monstrosity', 'landcycling']
    kaheera_types = ['Cat', 'Elemental', 'Nightmare', 'Dinosaur', 'Beast']
    if c.mana_value % 2 == 0:
        categories.append('gyruda')
    if c.mana_value % 2 == 1 or 'Land' in c.types:
        categories.append('obosh')
    if c.mana_value > 2 or 'Land' in c.types:
        categories.append('keruga')
    if 'Instant' in first_type or 'Sorcery' in first_type or c.mana_value <= 2:
        categories.append('lurrus')
    if 'Creature' not in first_type or [x for x in kaheera_types if x in first_type]:
        categories.append('kaheera')

    cost_split = c.mana_cost_str.replace(' // ', '').split('}')
    if len(cost_split) == len(set(cost_split)):
        categories.append('jegantha')

    zirda_regex = re.compile('^[^"]+:.+$')
    if 'Instant' in first_type or 'Sorcery' in first_type or [x for x in activated_keywords if x in c.keywords] or \
            [x for x in first_oracle if zirda_regex.match(x)]:
        categories.append('zirda')

    c.categories = categories
    return categories
