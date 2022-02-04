from math import ceil
from typing import Dict, Tuple

from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.types.card import Card
from shared.types.deck import Deck


def check_adam(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Adam of the Ironside' not in d.sideboard:
        return deck_check_statuses[0], ''
    creatures = [x for x in d.mainboard if x in c and 'Creature' in c[x].types]
    creature_count = sum([d.mainboard[x] for x in creatures])
    if creature_count < 12:
        return deck_check_statuses[1], \
            f'Too few creatures for Adam of the Ironside: expected 12, got {creature_count}'

    # if we are here, there are 12 or more creatures, therefore 1 or more distinct creatures
    first_creature_types = c[creatures[0]].types.split(' — ')[1].split(' ')
    shared_types = [x for x in first_creature_types if not [y for y in creatures if x not in c[y].types]]
    if not shared_types:
        return deck_check_statuses[1], 'The creature type clause on Adam of the Ironside is not fulfilled'
    return deck_check_statuses[0], 'The deck qualifies for Adam of the Ironside!'


def check_alvarez(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Alvarez of the Huntsman' not in d.sideboard:
        return deck_check_statuses[0], ''
    lands = [x for x in d.mainboard if x in c and 'Land' in c[x].types]
    land_count = sum([d.mainboard[x] for x in lands])
    all_count = sum([x for x in d.mainboard.values()])
    if land_count * 2 < all_count:
        return deck_check_statuses[1],\
            f'Too few lands for Alvarez of the Huntsman: expected {ceil(all_count / 2)}, got {land_count}'
    return deck_check_statuses[0], 'The deck qualifies for Alvarez of the Huntsman!'


def check_garth(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Garth of the Chimera' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'garth' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Garth of the Chimera: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Garth of the Chimera!'


def check_harriet(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Harriet of the Pioneer' not in d.sideboard:
        return deck_check_statuses[0], ''
    vehicles = [x for x in d.mainboard if x in c and 'Vehicle' in c[x].types]
    vehicle_count = sum([d.mainboard[x] for x in vehicles])
    if vehicle_count < 12:
        return deck_check_statuses[1],\
            f'Too few vehicles for Harriet of the Pioneer: expected 12, got {vehicle_count}'
    return deck_check_statuses[0], 'The deck qualifies for Harriet of the Pioneer!'


def check_holcomb(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Holcomb of the Peregrine' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if d.mainboard[x] != 2 and (x not in c or 'Land' not in c[x].types)]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Holcomb of the Peregrine: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Holcomb of the Peregrine!'


def check_hugo(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Hugo of the Shadowstaff' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'hugo' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Hugo of the Shadowstaff: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Hugo of the Shadowstaff!'


def check_mable(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Mable of the Sea\'s Whimsy' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'mable' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Mable of the Sea\'s Whimsy: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Mable of the Sea\'s Whimsy!'


def check_marisa(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Marisa of the Gravehowl' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'marisa' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Marisa of the Gravehowl: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Marisa of the Gravehowl!'


def check_searle(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Searle of the Tempest' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'searle' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Searle of the Tempest: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Searle of the Tempest!'


def check_tabia(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Tabia of the Lionheart' not in d.sideboard:
        return deck_check_statuses[0], ''
    card_types = ['Creature', 'Planeswalker', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Tribal']
    type_breakdown = {x: [y for y in d.mainboard if y in c and x in c[y].faces[0].types] for x in card_types}
    type_counts = {x: sum([d.mainboard[y] for y in z]) for x, z in type_breakdown.items()}
    bad_types = [x for x, z in type_counts.items() if z > 8]
    if bad_types:
        return deck_check_statuses[1], \
            'The following types don\'t qualify for Tabia of the Lionheart: ' + ', '.join(bad_types)
    return deck_check_statuses[0], 'The deck qualifies for Tabia of the Lionheart!'


def convert_mana_cost(mana_cost: Dict[str, int]) -> str:
    return ' '.join([f'{x}-{mana_cost[x]}' for x in sorted(mana_cost)])


def check_valencia(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Valencia of the Concordant' not in d.sideboard:
        return deck_check_statuses[0], ''
    # legitimately what the fuck
    mana_costs = {convert_mana_cost(c[x].mana_cost) for x in d.mainboard if 'Land' not in c[x].types}  # type: ignore
    if len(mana_costs) > 4:
        return deck_check_statuses[1],\
            f'Too many mana costs for Valencia of the Concordant: expected 4, got {len(mana_costs)}'
    return deck_check_statuses[0], 'The deck qualifies for Valencia of the Concordant!'


def check_asabeth(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Asabeth of the Intrepid' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x, y in d.mainboard.items() if x in c and 'Land' in c[x].faces[0].types and y > 1]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Asabeth of the Intrepid: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Asabeth of the Intrepid!'


def check_ashe(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Ashe of the Winged Steed' not in d.sideboard:
        return deck_check_statuses[0], ''
    good = sum(y for x, y in d.mainboard.items() if x in c and 'ashe' in c[x].categories)
    if good < 12:
        return deck_check_statuses[1],\
            f'Too few Dragons for Ashe of the Winged Steed: expected 12, got {good}'
    return deck_check_statuses[0], 'The deck qualifies for Ashe of the Winged Steed!'


def check_telsi(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Dr. Telsi of the Ark' not in d.sideboard:
        return deck_check_statuses[0], ''
    good = sum(y for x, y in d.mainboard.items() if x in c and 'telsi' in c[x].categories)
    if good < 12:
        return deck_check_statuses[1],\
            f'Too few Control cards for Dr. Telsi of the Ark: expected 12, got {good}'
    return deck_check_statuses[0], 'The deck qualifies for Dr. Telsi of the Ark!'


def check_lilia(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Lilia of the Soul' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'lilia' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Lilia of the Soul: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Lilia of the Soul!'


def check_tinbeard(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Tinbeard of the Brine' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'tinbeard' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Tinbeard of the Brine: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Tinbeard of the Brine!'


def check_vir(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Vir of the Starskipper' not in d.sideboard:
        return deck_check_statuses[0], ''

    combos = [
        'white', 'blue', 'black', 'red', 'green',
        'white/blue', 'blue/black', 'black/red', 'red/green', 'green/white',
        'white/black', 'blue/red', 'black/green', 'red/white', 'green/blue'
    ]
    bad_combos = []
    for i in combos:
        color_set = set(i.split('/'))
        good = False
        for j in d.mainboard:
            if j in c:
                colors = set(c[j].colors)
                if not (colors ^ color_set):
                    good = True
                    break
        if not good:
            bad_combos.append(i)

    if bad_combos:
        return deck_check_statuses[1],\
            'The following color combos don\'t qualify for Vir of the Starskipper: ' + ', '.join(bad_combos)
    return deck_check_statuses[0], 'The deck qualifies for Vir of the Starskipper!'
