import re

from shared.types.card import Card


def _is_typed(c: str) -> bool:
    return 'Island' in c or 'Plains' in c or 'Forest' in c or 'Swamp' in c or 'Mountain' in c


generated_regexes = {}


def generate_regexes() -> None:
    if 'mable' in generated_regexes:
        return

    generated_regexes['mable'] = re.compile(r'\bFlash\b')
    marisa_words = ['die', 'dies', 'died', 'dying', 'destroy', 'destroys', 'destroyed', 'graveyard',
                    'graveyards', 'mill', 'mills', 'milled']
    marisa_regex_str = r'\b({x})\b'.format(x='|'.join(marisa_words))
    generated_regexes['marisa'] = re.compile(marisa_regex_str, re.I)

    # we try to find "target", but "becomes a target", Searle himself and Dack's ult are false positives.
    # the way regex works is that it tries to fulfill earlier conditions first.
    # so a card with "becomes a target" won't be considered as "target".
    # searle_regex_str = r'becomes a target|becomes the target|[”"][^”"]+[”"]|targets|target'
    searle_words = ['becomes a', 'change a', 'is a', 'with a', 'additional', 'all', 'choosing',
                    'could', 'deck', 'it', 'its', 'only', 'new', 'same', 'that', 'the', 'those',
                    'was', 'with one or more', 'with a single', 'would']  # by Cajun
    searle_words_join = '|'.join([f'{x} target' for x in searle_words])
    searle_regex_str = rf'["“][^”"]*[”"]|targeted|protection|{searle_words_join}|target'
    generated_regexes['searle'] = re.compile(searle_regex_str, re.I)

    ashe_regex_str = '\bdragon\b|^changeling\b|^changeling$'
    generated_regexes['ashe'] = re.compile(ashe_regex_str, re.I)

    telsi_words = ['gain control', 'gains control', 'gained control', 'exchange control']
    telsi_regex_str = r'\b({x})\b'.format(x='|'.join(telsi_words))
    generated_regexes['telsi'] = re.compile(telsi_regex_str, re.I)

    tinbeard_words = ['artifact', 'artifacts', 'treasure', 'treasures', 'pirate', 'pirates']
    tinbeard_regex_str = r'\b({x})\b'.format(x='|'.join(tinbeard_words))
    generated_regexes['tinbeard_oracle'] = re.compile(tinbeard_regex_str, re.I)

    tinbeard_words_type = ['Land', 'Artifact', 'Pirate']
    tinbeard_regex_str_type = r'\b({x})\b'.format(x='|'.join(tinbeard_words_type))
    generated_regexes['tinbeard_type'] = re.compile(tinbeard_regex_str_type, re.I)

    lilia_words = [r'\+1/\+1 counter', 'harmonize']
    lilia_regex_str = r'\b({x})\b'.format(x='|'.join(lilia_words))
    generated_regexes['lilia'] = re.compile(lilia_regex_str, re.I)


def add_card_categories(c: Card) -> list[str]:
    """
    Add card categories to a card object inplace.
    :param c: the card to modify
    :return: the categories added
    """
    generate_regexes()
    # Since MSEM does not have MDFCs yet, all CMC checks and oracle checks are done to the joined oracle/CMC.

    lower_oracle = c.oracle.lower()
    first_half_type = c.types.split(' // ')[0]
    # reminder_regex = re.compile(r'\((.+?)\)')
    # no_reminder_oracle = re.sub(reminder_regex, '', lower_oracle)
    categories: list[str] = []
    if c.mana_value in [0, 1, 3]:
        categories.append('hugo')

    if 'Instant' in c.types or generated_regexes['mable'].search(c.oracle) or 'Land' in first_half_type:
        categories.append('mable')
    if 'Creature' not in first_half_type:
        categories.append('garth')

    if 'Land' in first_half_type or generated_regexes['marisa'].search(lower_oracle):
        categories.append('marisa')
    if 'Land' in first_half_type or 'Aura' in c.types or 'Equipment' in c.types or \
            'target' in generated_regexes['searle'].findall(lower_oracle):
        categories.append('searle')

    if 'Dragon' in c.types or generated_regexes['ashe'].search(c.oracle):
        categories.append('ashe')

    if generated_regexes['telsi'].search(c.oracle):
        categories.append('telsi')

    if 'Land' in first_half_type or generated_regexes['lilia'].search(c.oracle):
        categories.append('lilia')

    if generated_regexes['tinbeard_oracle'].search(c.oracle) or generated_regexes['tinbeard_type'].search(c.types):
        categories.append('tinbeard')

    if 'Land' in first_half_type:
        if '~ enters the battlefield tapped if you control another nonbasic land.' in c.t_oracle:
            categories.append('abandoned-land')
        if 'Angeltouched' in c.name:
            categories.append('angelland')
        if 'Brilliant' in c.name:
            categories.append('filterland')
        if 'Legendary' in c.types and '{T}, Pay 1 life: Add ' in c.oracle and ', Exile ~ from your hand:' in c.t_oracle:
            categories.append('auroraland')
        if c.name in ['Bleak Shoreline', 'Calmed Battleground', 'Sunlit Ruins', 'Cloudcover Heights', 'Deeplife Cavern',
                      'Forbidding Isle', 'Frigid Highlands', 'Gleaming Hot Springs', 'Idyllic Oasis', 'Charred Marsh']:
            categories.append('tricheck')
        if '{T}, Pay 1 life: Add ' in c.oracle and '{T}, Pay 1 life, Sacrifice ~' in c.t_oracle:
            categories.append('colorfetch')
        if 'Desert' in c.types and '~ becomes a' in c.t_oracle and 'enters the battlefield tapped' in c.oracle:
            categories.append('desert-manland')
        if '{T}, Pay 1 life: Add ' in c.oracle and 'Investigate' in c.oracle:
            categories.append('clue-painland')
        if 'unless you have two or more opponents' in c.oracle:
            categories.append('edhland')
        if c.produces_len == 3 and '{T}, Pay 1 life: Add ' in c.oracle:
            categories.append('painland')
        if 'reveal' in c.oracle and 'If you don\'t, ~ enters the battlefield tapped' in c.oracle:
            categories.append('shadowland')
        if 'Choose a basic land type other than' in c.oracle:
            categories.append('shiftland')
        if 'you may pay 2 life' in c.oracle and 'Search' in c.oracle:
            categories.append('shockfetch')
        if 'You may untap ~ during each other player\'s untap step' in c.t_oracle:
            categories.append('sunriseland')
        if 'torment yourself' in c.oracle:
            categories.append('tormentland')
        if 'Animus' in c.types and _is_typed(c.types):
            categories.append('animus')
        if c.produces_len == 2 and 'unless you control a' in c.oracle and _is_typed(c.types):
            categories.append('koraland')
        if c.produces_len == 2 and 'lose 1 life unless you control two' in c.oracle:
            categories.append('plagueland')
        if c.produces_len == 3 and _is_typed(c.types):
            categories.append('typed-triland')

    modal = False
    if '•' in c.oracle:
        categories.append('modal')
        modal = True
    if 'Artifact' in first_half_type or 'Enchantment' in first_half_type or modal:
        categories.append('cryptic')

    if 'Enchantment' in first_half_type or 'Legendary' in first_half_type:
        categories.append('storied')

    if 'First mate—' in c.oracle or 'First mate —' in c.oracle:
        categories.append('first-mate')

    if 'Instant' in first_half_type and c.mana_value == 2 and 'blue' in c.colors:
        categories.append('cane-dancer')

    c.categories = categories
    return categories
