from typing import Dict, Tuple

from shared.helpers.deckcheck.core import DeckCheckStatus, deck_check_statuses
from shared.types.card import Card
from shared.types.deck import Deck


def check_gyruda(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Gyruda, Doom of Depths' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'gyruda' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Gyruda, Doom of Depths: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Gyruda, Doom of Depths!'


def check_jegantha(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Jegantha, the Wellspring' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'jegantha' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Jegantha, the Wellspring: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Jegantha, the Wellspring!'


def check_kaheera(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Kaheera, the Orphanguard' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'kaheera' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Kaheera, the Orphanguard: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Kaheera, the Orphanguard!'


def check_keruga(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Keruga, the Macrosage' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'keruga' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Keruga, the Macrosage: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Keruga, the Macrosage!'


def check_lurrus(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Lurrus of the Dream-Den' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'lurrus' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Lurrus of the Dream-Den: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Lurrus of the Dream-Den!'


def check_obosh(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Obosh, the Preypiercer' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'obosh' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Obosh, the Preypiercer: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Obosh, the Preypiercer!'


def check_zirda(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Zirda, the Dawnwaker' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if x not in c or 'zirda' not in c[x].categories]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Zirda, the Dawnwaker: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Zirda, the Dawnwaker!'


def check_lutri(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Lutri, the Spellchaser' not in d.sideboard:
        return deck_check_statuses[0], ''
    bad_cards = [x for x in d.mainboard if d.mainboard[x] != 1 and (x not in c or 'Land' not in c[x].types)]
    if bad_cards:
        return deck_check_statuses[1],\
            'The following cards don\'t qualify for Lutri, the Spellchaser: ' + ', '.join(bad_cards)
    return deck_check_statuses[0], 'The deck qualifies for Lutri, the Spellchaser!'


def check_yorion(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Yorion, Sky Nomad' not in d.sideboard:
        return deck_check_statuses[0], ''
    mainboard_len = sum(d.mainboard.values())
    if mainboard_len < 80:
        return deck_check_statuses[1], f'The deck is too small for Yorion, Sky Nomad: expected 80, got {mainboard_len}'
    return deck_check_statuses[0], 'The deck qualifies for Yorion, Sky Nomad!'


def check_umori(d: Deck, c: Dict[str, Card]) -> Tuple[DeckCheckStatus, str]:
    if 'Umori, the Collector' not in d.sideboard:
        return deck_check_statuses[0], ''
    types = ['Creature', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 'Planeswalker', 'Tribal']
    good_type = ''
    for i in types:
        bad_cards = [x for x in d.mainboard if x not in c or ('Land' not in c[x].types or i not in c[x].types)]
        if not bad_cards:
            good_type = i
    if not good_type:
        return deck_check_statuses[1], 'The deck does not qualify for Umori, the Collector!'
    return deck_check_statuses[0], f'The deck qualifies for Umori, the Collector with the type {good_type}!'
