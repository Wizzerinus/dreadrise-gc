import io
import os
from math import ceil
from typing import Any, Dict, List, Literal, Optional, Tuple, cast

from flask import Blueprint, Response, abort, request, send_file
from PIL import Image, ImageDraw, ImageFont
from pymongo.database import Database

from shared.helpers.db_loader import load_cards_from_decks
from shared.helpers.util2 import build_deck
from shared.types.card import Card
from shared.types.deck import Deck
from website.util import get_dist, split_database

b_imagery = Blueprint('imagery', __name__)


def generate_colors_from_deck(cards: Dict[str, Card], deck: Deck, full_width: int = 150,
                              angle: Literal[0, 90, 180, 270] = 0) -> Response:
    counts = {'white': 0, 'blue': 0, 'black': 0, 'red': 0, 'green': 0}
    colors = {'white': (255, 255, 128), 'blue': (0, 0, 200), 'black': (10, 10, 10),
              'red': (200, 0, 0), 'green': (0, 200, 0)}
    for i, c in deck.mainboard.items():
        if i not in cards:
            continue
        for j, k in cards[i].mana_cost.items():
            if j in counts:
                counts[j] += k * c

    count_sum = sum(counts.values())
    full_height = 25
    image = Image.new('RGB', (full_width, full_height))
    if count_sum:
        normalized_counts = {x: y * full_width / count_sum for x, y in counts.items()}

        stops: List[Tuple[Optional[str], int]] = [(None, 0)]
        last_stop: float = 0
        for color, n in normalized_counts.items():
            last_stop += n
            stops.append((color, ceil(last_stop)))

        for h in range(1, 6):
            if stops[h][1] > stops[h - 1][1]:
                image.paste((128, 128, 128), (stops[h - 1][1], 0, stops[h][1], full_height))  # type: ignore
                image.paste(colors[stops[h][0]],  # type: ignore
                            (stops[h - 1][1] + 1, 1, stops[h][1] - 1, full_height - 1))

    crop_bytes = io.BytesIO()
    if angle:
        image = image.transpose(getattr(Image, f'ROTATE_{angle}'))
    image.save(crop_bytes, 'PNG')
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/png')


def generate_curve_from_deck(cards: Dict[str, Card], deck: Deck, full_height: int = 175) -> Response:
    total_columns = 9  # 0, 1, 2, 3, 4, 5, 6, 7+, X
    counts = [0 for _ in range(total_columns)]
    colors = [(200 - 12 * x, 200 - 12 * x, 200 - 12 * x) for x in range(total_columns)]
    texts = [str(x) for x in range(total_columns - 2)] + [f'{total_columns - 2}+', 'X']
    for i, c in deck.mainboard.items():
        if i not in cards:
            continue
        if cards[i].main_type == 'land':
            continue
        if 'X' in cards[i].mana_cost:
            counts[8] += c
        else:
            counts[min(7, cards[i].mana_value)] += c

    count_sum = max(counts)

    column_width = 25
    number_height = 25
    image = Image.new('RGB', (total_columns * column_width, full_height + number_height), (255, 255, 255))

    if count_sum:
        drawer = ImageDraw.Draw(image)
        normalized_counts = [x * full_height // count_sum for x in counts]
        path = os.path.dirname(os.path.abspath(__file__))
        fnt = ImageFont.truetype(f'{path}/../../inconsolata.ttf', column_width - 2)

        for h in range(total_columns):
            image.paste(colors[h],  # type: ignore
                        (h * column_width, full_height - normalized_counts[h], (h + 1) * column_width, full_height))
            dx = 0 if total_columns - h == 2 else column_width // 4
            drawer.text((h * column_width + dx, full_height), text=texts[h], fill=(0, 0, 0), font=fnt)  # type: ignore
            if counts[h]:
                x = h * column_width + (0 if counts[h] > 9 else column_width // 4)
                y = full_height - normalized_counts[h] if normalized_counts[h] > number_height * 1.25 \
                    else full_height - number_height - normalized_counts[h]
                drawer.text((x, y), text=str(counts[h]), fill=(0, 0, 0), font=fnt)  # type: ignore

    crop_bytes = io.BytesIO()
    image.save(crop_bytes, 'PNG')
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/png')


@b_imagery.route('/colors/<deck_id>')
@split_database
def generate_colors(db: Database, deck_id: str) -> Response:
    deck = db.decks.find_one({'deck_id': deck_id})
    if not deck:
        abort(404)
    cards = load_cards_from_decks(get_dist(), [Deck().load(deck)])
    return generate_colors_from_deck(cards, Deck().load(deck), 150, 0)


@b_imagery.route('/colors-rotated/<deck_id>')
@split_database
def generate_colors_rotated(db: Database, deck_id: str) -> Response:
    deck = db.decks.find_one({'deck_id': deck_id})
    if not deck:
        abort(404)
    cards = load_cards_from_decks(get_dist(), [Deck().load(deck)])
    return generate_colors_from_deck(cards, Deck().load(deck), 145, 90)


@b_imagery.route('/colors', methods=['POST'])
def generate_colors_api() -> Response:
    req = cast(Dict[str, Any], request.get_json())
    deck_list = req['deck_list']
    deck = build_deck(deck_list)
    cards = load_cards_from_decks(get_dist(), [deck])
    return generate_colors_from_deck(cards, deck)


@b_imagery.route('/curve/<deck_id>')
@b_imagery.route('/curve/<deck_id>/<int:height>')
@split_database
def generate_curve(db: Database, deck_id: str, height: int = 175) -> Response:
    deck = db.decks.find_one({'deck_id': deck_id})
    if not deck:
        abort(404)
    cards = load_cards_from_decks(get_dist(), [Deck().load(deck)])
    return generate_curve_from_deck(cards, Deck().load(deck), height)


@b_imagery.route('/curve', methods=['POST'])
def generate_curve_api() -> Response:
    req = cast(Dict[str, Any], request.get_json())
    deck_list = req['deck_list']
    deck = build_deck(deck_list)
    cards = load_cards_from_decks(get_dist(), [deck])
    return generate_curve_from_deck(cards, deck)
