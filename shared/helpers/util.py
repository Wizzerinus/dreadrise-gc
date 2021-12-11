from typing import Any, List, Optional

from shared.card_enums import Legality, ManaDict


def clean_name(s: Optional[str]) -> str:
    """
    Cleans the name by removing bad symbols from it, returns a name possible to use in an URL.
    :param s: the name to process
    :return: the processed name
    """
    if not s:
        return ''

    s = s.encode('ascii', 'ignore').decode('ascii')
    s = s.replace('(', '').replace(')', '').replace(':', '-').replace('\'', '')
    return s.replace(' // ', '--').replace(', ', '-').replace(' ', '-')\
        .replace('/', '-').replace('\'', '').replace(':', '').lower()


def clean_card(name: str) -> str:
    """
    Processes card names obtained from different sources (MTGO, Cockatrice, etc.)
    :param name: the name to clean
    :return: the name of the card in database
    """
    name = name.split('_')[0]
    if '/' in name and '//' not in name:
        name = name.replace('/', ' // ')
    if '//' in name and ' // ' not in name:
        name = name.replace('//', ' // ')

    return name


def sum_mana_costs(costs: List[ManaDict]) -> ManaDict:
    """
    Adds all given mana costs without modifying them and returns the sum.
    :param costs: the mana cost to add
    :return: the resulting mana cost
    """
    ans: ManaDict = {}
    for i in costs:
        for j, k in i.items():
            ans[j] = ans.get(j, 0) + k
    return ans


def int_def(a: Any, default: int = 0) -> int:
    """
    Converts an object into Int, with a default value.
    :param a: the object to convert into int
    :param default: the default value if conversion failed
    :return: the resulting int
    """
    if a is int:
        return a
    try:
        return int(a)
    except ValueError:
        return default


def ireg(s: str) -> dict:
    return {'$regex': s, '$options': 'i'}


def get_legality_color(e: Legality) -> str:
    if e == 'legal':
        return 'success'
    if e == 'restricted':
        return 'warning'
    if e == 'banned':
        return 'danger'
    return 'secondary'


def shorten_name(s: str, max_len: int = 19) -> str:
    if len(s) < max_len:
        return s
    return s[:max_len - 3] + '...'
