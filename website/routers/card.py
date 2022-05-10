import io
from typing import Literal

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file
from PIL import Image
from pymongo.database import Database
from werkzeug import Response

from shared import fetch_tools
from shared.helpers.db_loader import load_expansions
from shared.helpers.util2 import get_card_art
from shared.types.card import Card
from website.util import get_dist, split_database, split_import

b_card = Blueprint('card', __name__)


@b_card.route('/<card_id>')
@split_database
def single_card(db: Database, card_id: str) -> str:
    dist = get_dist()
    card_obj = db.cards.find_one({'card_id': card_id})
    if not card_obj:
        flash(f'Card with ID {card_id} not found.')
        abort(404)
    card = Card().load(card_obj)
    class1 = 'col-12 col-lg-6 col-xl-5' if card.layout == 'split' else \
        'col-12 col-md-6 col-lg-4 col-xxl-3' if not card.image_join() else 'col-12 col-lg-8 col-xl-6'
    class2 = 'col-12 col-lg-6 col-xl-7' if card.layout == 'split' else \
        'col-12 col-md-6 col-lg-8' if not card.image_join() else 'col-12 col-lg-4 col-xl-6'
    expansions = load_expansions(dist)
    return render_template('card/single.html', data=card, cls1=class1, cls2=class2, sets=expansions)


def rotated_image(url: str, angle: Literal[0, 90, 180, 270], max_width: int = 0) -> Response:
    if angle == 0 and max_width <= 0:
        return redirect(url)
    img = fetch_tools.fetch_bytes(url)
    image_obj = Image.open(io.BytesIO(img))
    rotated_bytes = io.BytesIO()
    if angle != 0:
        image_obj = image_obj.transpose(getattr(Image, f'ROTATE_{angle}'))
    if max_width > 0:
        cur_width, cur_height = image_obj.size
        if cur_width > max_width:
            image_obj = image_obj.resize((max_width, int(max_width / cur_width * cur_height)))
    image_obj.save(rotated_bytes, 'JPEG', quality=70)
    rotated_bytes.seek(0)
    return send_file(rotated_bytes, mimetype='image/jpeg')


@b_card.route('/image/<name>')
@split_database
def card_image(db: Database, name: str) -> Response:
    card = db.cards.find_one({'card_id': name})
    if not card:
        abort(404)

    return rotated_image(card['image'], split_import().GetRotationAngle(Card().load(card)))


@b_card.route('/face-image/<name>/<int:n>')
@split_database
def face_image(db: Database, name: str, n: int) -> Response:
    card = db.cards.find_one({'card_id': name})
    if not card:
        abort(404)

    card_obj = Card().load(card)
    max_width = 0
    if request.args.get('searching'):
        max_width = (len(card_obj.fixed_faces) - 1) * 320
    return rotated_image(card_obj.faces[n].image, split_import().GetRotationAngle(Card().load(card)),
                         max_width=max_width)


@b_card.route('/art/<name>')
@split_database
def art_crop(db: Database, name: str) -> Response:
    card_obj = db.cards.find_one({'card_id': name})
    if not card_obj:
        abort(404)
    card = Card().load(card_obj)

    constants = split_import()
    if 'cropping' not in constants.EnabledModules:
        return redirect(constants.GetCropLocation(card))
    image = get_card_art(constants, card)
    crop_bytes = io.BytesIO()
    image.save(crop_bytes, 'JPEG', quality=70)
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/jpeg')


@b_card.route('/art-header/<name>')
@split_database
def art_header(db: Database, name: str) -> Response:
    card = db.cards.find_one({'card_id': name})
    if not card:
        abort(404)
    image = get_card_art(split_import(), Card().load(card))
    image = image.crop((0, 70, 225, 105))
    crop_bytes = io.BytesIO()
    image.save(crop_bytes, 'JPEG', quality=70)
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/jpeg')
