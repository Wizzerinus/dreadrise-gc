import io
from typing import Literal, cast

from flask import Blueprint, abort, flash, redirect, render_template, send_file
from PIL import Image
from pymongo.database import Database
from werkzeug import Response

from shared import fetch_tools
from shared.helpers.db_loader import load_expansions
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


def rotated_image(url: str, angle: Literal[0, 90, 180, 270]) -> Response:
    if angle == 0:
        return redirect(url)
    img = fetch_tools.fetch_bytes(url)
    image_obj = Image.open(io.BytesIO(img))
    rotated_bytes = io.BytesIO()
    image_obj.transpose(getattr(Image, f'ROTATE_{angle}')).save(rotated_bytes, 'JPEG', quality=70)
    rotated_bytes.seek(0)
    return send_file(rotated_bytes, mimetype='image/jpeg')


@b_card.route('/image/<name>')
@split_database
def card_image(db: Database, name: str) -> Response:
    card = db.cards.find_one({'card_id': name})
    if not card:
        abort(404)

    return rotated_image(card['image'], split_import().get_rotation_angle(Card().load(card)))


@b_card.route('/face-image/<name>/<int:n>')
@split_database
def face_image(db: Database, name: str, n: int) -> Response:
    card = db.cards.find_one({'card_id': name})
    if not card:
        abort(404)

    return rotated_image(card['faces'][n]['image'], split_import().get_rotation_angle(Card().load(card)))


def art_crop_local(card: Card) -> Image.Image:
    img = fetch_tools.fetch_bytes(card.image)

    saga_like = ['Saga', 'Discovery', 'Realm', 'Quest']
    is_saga = len([x for x in saga_like if x in card.types]) > 0

    if 'Mystery' in card.types:
        art_coords = (30, 50, 282, 246)
        img = cast(bytes, fetch_tools.fetch_bytes(card.faces[1].image, is_bytes=True))
    elif is_saga:  # TODO: omg this quality is garbage. maybe fixing next time
        art_coords = (160, 110, 286, 208)
    elif card.layout == 'split':
        art_coords = (48, 45, 210, 171)
    elif 'Planeswalker' in card.types and card.oracle.count('\n') >= 3:
        art_coords = (44, 42, 268, 216)
    else:
        art_coords = (30, 50, 282, 246)

    image_obj = Image.open(io.BytesIO(img))
    return image_obj.crop(art_coords).resize((225, 175))


@b_card.route('/art/<name>')
@split_database
def art_crop(db: Database, name: str) -> Response:
    card_obj = db.cards.find_one({'card_id': name})
    if not card_obj:
        abort(404)
    card = Card().load(card_obj)

    constants = split_import()
    if 'cropping' not in constants.enabled_modules:
        return redirect(constants.get_crop_location(card))
    image = art_crop_local(card)
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
    image = art_crop_local(Card().load(card))
    image = image.crop((0, 70, 225, 105))
    crop_bytes = io.BytesIO()
    image.save(crop_bytes, 'JPEG', quality=70)
    crop_bytes.seek(0)
    return send_file(crop_bytes, mimetype='image/jpeg')
