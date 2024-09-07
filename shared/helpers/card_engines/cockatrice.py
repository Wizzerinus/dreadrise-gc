import logging
from typing import Callable, TypeVar, cast

import arrow

from shared.card_enums import Color, color_symbols_to_colors, colors
from shared.helpers.exceptions import ScrapeError
from shared.helpers.magic import get_rarity, process_mana_cost_dict, add_braces
from shared.helpers.util import int_def
from shared.types.card import Card, CardFace
from shared.types.set import Expansion

logger = logging.getLogger('dreadrise.engine.cockatrice')


C = TypeVar('C', bound=Card)
F = TypeVar('F', bound=CardFace)


def process_cockatrice_card(card: dict, image_getter: Callable[[dict], str], fcls: type[F]) -> F:
    if 'name' not in card:
        raise ScrapeError('Invalid card dictionary.')
    logger.debug('Processing card {name}'.format(name=card['name']))
    f = fcls()

    f.name = card['faceName'] if 'faceName' in card else card['name']
    if ' // ' in f.name or ' (' in f.name:
        logger.warning(f'Card {f.name} has // in its face name')
    f.name = f.name.split('_')[0].split(' (')[0]
    manaCost = add_braces(card['manaCost'])
    f.mana_cost_str = manaCost
    f.mana_cost = process_mana_cost_dict(manaCost)
    f.mana_value = card['faceConvertedManaCost'] \
        if 'faceConvertedManaCost' in card \
        else card['convertedManaCost']
    f.oracle = card['text'] if 'text' in card else ''
    f.types = card['type']
    f.colors = [color_symbols_to_colors[x] for x in card['colors']]
    f.cast_colors = [cast(Color, x) for x in f.mana_cost if x in colors]
    f.image = image_getter(card)

    for i in 'power', 'toughness', 'loyalty':
        if i in card:
            setattr(f, i, int_def(card[i]))

    return f


def process_cockatrice_set(cset: dict, image_getter: Callable[[str, dict], str], formats: dict[str, str],
                           ccls: type[C], fcls: type[F]) -> \
        tuple[list[C], Expansion]:
    if 'cards' not in cset or 'name' not in cset or 'code' not in cset:
        raise ScrapeError('Invalid cockatrice set dictionary.')

    set_name = cset['name']
    set_id = cset['code']
    logger.info(f'Processing set {set_name}')

    card_faces_dict = {}
    for i in cset['cards']:
        card_faces_dict[i['id']] = process_cockatrice_card(i, lambda dct: image_getter(set_id, dct), fcls)

    answer: list[C] = []
    for i in cset['cards']:
        if 'side' in i and i['side'] == 'b':
            continue

        c = ccls()
        c.layout = i['layout'].lower()
        c.faces = [card_faces_dict[i['id']]]
        if 'otherFaceIds' in i:
            c.faces.append(card_faces_dict[i['otherFaceIds'][0]])
        c.color_identity = list(set([color_symbols_to_colors[x] for x in i['colorIdentity']]))
        c.sets = [set_id]
        c.rarities = [get_rarity(i['rarity'])]
        c.categories = []
        c.legality = {}
        for leg in i['legalities']:
            fmt = formats.get(leg['format'], None)
            if fmt:
                c.legality[fmt] = leg['legality'].lower()
        c.max_count = 4
        answer.append(c)

    logger.info(f'{set_name}: {len(answer)} cards')

    ex = Expansion()
    ex.name = set_name
    ex.code = set_id
    ex.release_date = arrow.get(cset['releaseDate']).datetime
    return answer, ex
