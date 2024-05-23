from math import ceil

from shared.helpers.util2 import get_card_sorter
from shared.types.card import Card
from shared.types.deck import Deck


def generate_masonry(d: Deck, cards: dict[str, Card], columns: int = 4) -> tuple[list[str], list[str], list[str]]:
    """
    Generate a masonry-like display for a deck.
    :param d: the deck to generate the display for.
    :param cards: the dictionary with cards in the deck
    :param columns: the number of columns in the main part
    :return: a tuple consisting of the main part, the land part, and the sideboard
    """
    answer: list[list[str]] = [[] for _ in range(columns)]
    answer_length: list[int] = [0 for _ in range(columns)]
    card_index: dict[str, int] = {}
    lands: list[str] = []
    sideboard: list[str] = []

    for k, v in d.mainboard.items():
        if k in cards and cards[k].main_type == 'land':
            for i in range(v):
                lands.append(k)
        else:
            card_index[k] = v

    for k, v in d.sideboard.items():
        for i in range(v):
            sideboard.append(k)

    for k, v in sorted(card_index.items(), key=lambda x: -x[1]):
        pending_length = min(answer_length)
        pending_column = [x for x in range(columns) if answer_length[x] == pending_length][0]
        for i in range(v):
            answer[pending_column].append(k)
        answer_length[pending_column] += v

    answer.sort(key=len, reverse=True)
    answer_length.sort(reverse=True)
    lands.sort()
    sideboard.sort(key=get_card_sorter(cards))

    # Reorganize answer to be evenly filled
    # """
    average_length = ceil(sum(answer_length) / columns)
    bad_columns = [(x, y - average_length) for x, y in enumerate(answer_length) if y > average_length]
    for col, overload in bad_columns:
        for j in range(overload):
            overload_card = answer[col][j + average_length]
            pending_length = min(answer_length)
            pending_column = [x for x in range(columns) if answer_length[x] == pending_length][0]
            answer[pending_column].append(overload_card)
    for i, arr in enumerate(answer):
        answer[i] = arr[:average_length]
        answer_length[i] = len(answer[i])
    # """

    # Convert into a modified type
    answer.sort(key=len, reverse=True)
    column_addition = []
    for x in range(max(answer_length)):
        for y in answer:
            if len(y) > x:
                column_addition.append(y[x])
            else:
                column_addition.append('')

    return column_addition, lands, sideboard
