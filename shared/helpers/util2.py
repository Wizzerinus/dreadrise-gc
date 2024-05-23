import io
import logging
import re
from importlib import import_module
from typing import Callable, cast

from PIL import Image

from shared import fetch_tools
from shared.card_enums import card_types
from shared.core_enums import Distribution, distributions
from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.dist_constants import DistConstants
from shared.types.set import Expansion

logger = logging.getLogger('dreadrise.util')
reminder_regex = re.compile(r' \((.+?)\)')


def build_deck(deck_list: list[tuple[int, str, int, bool, int]]) -> Deck:
    """
    Create a deck from the deck builder deck definition.
    :param deck_list: the deck builder definition.
    :return: the resulting Deck object.
    """
    d = Deck()
    d.mainboard = {y: x for x, y, _, z, _ in deck_list if not z}
    d.sideboard = {y: x for x, y, _, z, _ in deck_list if z}
    return d


def get_dist_constants(dist: Distribution) -> DistConstants:
    """
    Get the distribution constants for a specified distribution.
    :param dist: the distribution
    :return: the DistConstants object
    """
    return cast(DistConstants, import_module(f'dists.{dist}.constants'))


def update_distributions() -> None:
    """
    Update all distributions. Called when the web server is starting.
    :return: nothing
    """
    logger.info('Updating the distributions...')
    for i in distributions:
        if i != 'default':
            mod = get_dist_constants(i)
            try:
                mod.Update()
                logger.info(f'Updated {i}')
            except AttributeError:
                logger.info(f'Update function for {i} does not exist')


def get_card_sorter(cards: dict[str, Card]) -> Callable[[str], tuple[int, str]]:
    """
    Create the function sorting cards.
    :param cards: the card dictionary the cards should be drawn from
    :return: the resulting function, can be used as the key parameter
    """

    def card_sorter(name: str) -> tuple[int, str]:
        if name not in cards:
            return -1, name

        card = cards[name]
        try:
            type_index = card_types.index(card)
        except ValueError:
            type_index = 9

        return card.mana_value + type_index * 30, name

    return card_sorter


def calculate_color_data(deck: Deck, cards: dict[str, Card]) -> list[float]:
    """
    Calculate the color data for a deck.
    :param deck: the deck in question
    :param cards: the card dictionary including all the cards in the deck
    :return: list of 5 numbers - % of WUBRG symbols (from 0.0-1.0)
    """

    color_index = {'white': 0, 'blue': 1, 'black': 2, 'red': 3, 'green': 4}
    counts = [0, 0, 0, 0, 0]
    for i, c in deck.mainboard.items():
        if i not in cards:
            continue
        for j, k in cards[i].mana_cost.items():
            if j in color_index:
                counts[color_index[j]] += k * c

    count_sum = sum(counts)
    if not count_sum:
        return [x / 1.0 for x in counts]
    return [x / count_sum for x in counts]


def print_card(card: dict | Card) -> str:
    true_card = Card().load(card) if isinstance(card, dict) else card
    card_face = true_card.faces[0]
    name, cost, oracle = card_face.name, card_face.mana_cost_str, card_face.oracle
    ctype, cpow, ctou, cloy = card_face.types, card_face.power, card_face.toughness, card_face.loyalty
    oracle = reminder_regex.sub('', oracle)
    if 'Creature' in ctype:
        power_text = f'{cpow}/{ctou}'
    elif 'Planeswalker' in ctype:
        power_text = f'{cloy} SL'
    else:
        power_text = ''
    return f'{name} {cost} {power_text}\n{ctype}\n{oracle}'


def compare_cards(card1: dict | Card, card2: dict | Card, expansions: dict[str, Expansion] | None = None) -> str:
    """
    Compares two cards on having identical text. If expansion dict is passed, assumes the first card can be different
    from the second one if its first print is earlier. Otherwise, assumes the cards must be identical.
    :param card1: the "template" card
    :param card2: the "newly found" card
    :param expansions: used to determine dates
    :return: the comparison result
    """
    ct1, ct2 = print_card(card1), print_card(card2)
    if ct1 == ct2:
        return ''

    warning = True
    if expansions:
        sets1, sets2 = card1.get('sets', []), card2.get('sets', [])
        e1, e2 = [expansions[x].release_date for x in sets1], [expansions[x].release_date for x in sets2]
        warning = not e1 or not e2 or min(e1) > min(e2)

    warning_str = 'Warning!' if warning else 'Notice!'
    return f'{warning_str}\nCard 1: {ct1}\nCard 2: {ct2}\n'


def get_card_art(dc: DistConstants, card: Card) -> Image.Image:
    """
    Gets an image of a card art with a given size.
    :param dc: The constants of the distribution
    :param card: The card to process
    :return: The art-cropped image
    """

    if 'cropping' not in dc.EnabledModules:
        img = fetch_tools.fetch_bytes(dc.GetCropLocation(card))
        return Image.open(io.BytesIO(img))

    img = fetch_tools.fetch_bytes(card.image)

    saga_like = ['Saga', 'Discovery', 'Realm', 'Quest']
    is_saga = len([x for x in saga_like if x in card.types]) > 0

    if 'Mystery' in card.types:
        art_coords = (30, 50, 282, 246)
        img = cast(bytes, fetch_tools.fetch_bytes(card.faces[1].image, is_bytes=True))
    elif is_saga:  # omg this quality is garbage. maybe fixing next time
        art_coords = (160, 110, 286, 208)
    elif card.layout == 'split':
        art_coords = (48, 45, 210, 171)
    elif 'Planeswalker' in card.types and card.oracle.count('\n') >= 3:
        art_coords = (44, 42, 268, 216)
    else:
        art_coords = (30, 50, 282, 246)

    image_obj = Image.open(io.BytesIO(img))
    return image_obj.crop(art_coords).resize((225, 175))
