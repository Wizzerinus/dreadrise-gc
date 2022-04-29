import io
import json
import os
from math import ceil
from typing import Any, Dict, List, Tuple, cast

from flask import Blueprint, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
from werkzeug import Response

from shared.core_enums import Distribution
from shared.helpers.database import connect
from shared.helpers.util import get_wrapped_text, resize_with_ratio
from shared.helpers.util2 import get_card_art, get_dist_constants
from shared.types.card import Card
from website.util import get_dist

b_tools = Blueprint('tools', __name__)
b_tools_api = Blueprint('tools_api', __name__)

ColorDict = {
    'red': (255, 100, 100),
    'yellow': (255, 230, 20),
    'orange': (255, 190, 55),
    'blue': (20, 20, 240),
    'green': (20, 190, 20),
}
ImageCache: Dict[Tuple[str, str], Image.Image] = {}  # This gets recreated every hour so no memory leak


def generate_image_cache(dist: Distribution, cards: List[str], scale: Tuple[int, int]) -> Dict[str, Image.Image]:
    already_loaded = {x: ImageCache[(dist, x)] for x in cards if (dist, x) in ImageCache}
    cards = [x for x in cards if (dist, x) not in ImageCache]
    db = connect(dist)
    cards_found = [Card().load(x) for x in db.cards.find({'name': {'$in': cards}})]
    dc = get_dist_constants(dist)
    images_uncropped = [(x.name, get_card_art(dc, x)) for x in cards_found]
    images_cropped = [(x, resize_with_ratio(y, scale)) for x, y in images_uncropped]
    for x, y in images_cropped:
        ImageCache[(dist, x)] = y
        already_loaded[x] = y
    return already_loaded


def get_color(x: str) -> Tuple[int, int, int]:
    if x in ColorDict:
        return ColorDict[x]

    return int(x[1:3], 16), int(x[3:5], 16), int(x[5:7], 16)


@b_tools.route('/tier-maker')
def tiermaker() -> str:
    return render_template('tools/tier-maker.html', colors=json.dumps(ColorDict))


@b_tools_api.route('/tiers', methods=['POST'])
def tiers_api() -> Response:
    req = cast(Dict[str, Any], request.get_json())
    size = int(req['size'])
    tiers = cast(List[Dict[str, Any]], req['tiers'])
    tier_sizes = [len(x['cards']) for x in tiers]
    img_base_width = min(size, max(1, *tier_sizes))
    tier_heights = [ceil(x / img_base_width) for x in tier_sizes]
    colors = [get_color(x['color']) for x in tiers]
    img_base_height = sum(tier_heights)

    text_width = 160
    card_width = 130
    card_height = 100
    image_list = list({y for x in tiers for y in x['cards']})
    image_cache = generate_image_cache(get_dist(), image_list, (card_width, card_height))
    text_size = 18
    padding = 2
    full_w, full_h = text_width + img_base_width * card_width, img_base_height * card_height
    image = Image.new('RGBA', (full_w, full_h))
    image.paste((0, 0, 0), (0, 0, full_w, full_h))  # type: ignore
    path = os.path.dirname(os.path.abspath(__file__))
    fnt = ImageFont.truetype(f'{path}/../../opensans.ttf', text_size)
    drawer = ImageDraw.Draw(image)
    current_height = 0
    for tier, size, height, color in zip(tiers, tier_sizes, tier_heights, colors):
        inside_spacing = 0

        # Draw the header
        hh = current_height * card_height
        image.paste(color, (padding, hh + padding, text_width - 2 * padding,  # type: ignore
                            hh + card_height * height - padding))
        text = get_wrapped_text(tier['name'], fnt, text_width)  # type: ignore
        drawer.text((text_width / 2, hh + card_height / 2), text=text, fill=(0, 0, 0), font=fnt, anchor='mm')

        for card in tier['cards']:
            # Draw the card
            delta = inside_spacing * card_width + text_width
            if card in image_cache:
                image.paste(image_cache[card], (delta, hh, delta + card_width, hh + card_height))
            else:
                image.paste((256, 0, 0), (delta, hh, delta + card_width, hh + card_height))  # type: ignore

            inside_spacing += 1
            if inside_spacing >= size:
                inside_spacing = 0
                current_height += 1
                hh += card_height

    crop_bytes = io.BytesIO()
    image.save(crop_bytes, 'PNG', quality=70)
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/png')
