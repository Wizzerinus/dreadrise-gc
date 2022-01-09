from logging import getLogger
from typing import Any, Dict, List, cast

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from pymongo.database import Database
from pymongo.errors import OperationFailure
from werkzeug import Response

from shared.card_enums import Archetype, archetypes
from shared.helpers.util import clean_name, ireg
from shared.types.deck import Deck
from shared.types.deck_tag import ColorDeckRule, DeckRule, DeckTag, TextDeckRule
from website.util import privileges_required, requires_module, split_database

b_admin = Blueprint('admin', __name__)
b_admin_api = Blueprint('admin_api', __name__)

logger = getLogger('rise.admin')


@b_admin.route('/')
@privileges_required(['some_admin'])
@requires_module('admin')
def index() -> str:
    return render_template('admin/index.html', privs=g.actual_session['user']['privileges'])


@b_admin.route('/user-binding')
@privileges_required(['full_admin'])
@requires_module('admin')
def user_binding() -> str:
    return render_template('admin/user-binding.html')


@b_admin.route('/priv-manager')
@privileges_required(['full_admin'])
@requires_module('admin')
def privilege_manager() -> str:
    return render_template('admin/priv-manager.html')


@b_admin.route('/nicknames')
@privileges_required(['full_admin'])
@requires_module('admin')
def nickname_editor() -> str:
    return render_template('admin/nicknames.html')


@b_admin.route('/full-reruling')
@privileges_required(['deck_admin'])
@requires_module('archetyping')
@split_database
def rerun_all_rules(db: Database) -> Response:
    db.text_deck_rules.delete_many({'text': ''})
    rules = [TextDeckRule().load(x) for x in db.text_deck_rules.find()]
    tags = [DeckTag().load(x) for x in db.deck_tags.find()]

    added_rules = []
    for i in tags:
        if 'Color:' not in i.name and i.name != 'Colorless':
            l_rules = [x for x in rules if x.tag_id == i.tag_id]
            for j in range(3 - len(l_rules)):
                rule = TextDeckRule()
                rule.rule_id = f'text-{i.tag_id}-{j + len(l_rules) + 1}'
                rule.tag_id = i.tag_id
                rule.text = ''
                added_rules.append(rule.save())

    db.text_deck_rules.insert_many(added_rules)
    # TODO: prime the archetyping
    return redirect(url_for('.index'))


@b_admin.route('/tag-manager')
@privileges_required(['deck_mod'])
@requires_module('archetyping')
@split_database
def tag_manager(db: Database) -> str:
    tags = [DeckTag().load(x) for x in db.deck_tags.find()]
    rules: List[DeckRule] = [TextDeckRule().load(x) for x in db.text_deck_rules.find({'text': {'$ne': ''}})]
    rules += [ColorDeckRule().load(x) for x in db.color_deck_rules.find()]
    tag_dict = {x.tag_id: (x, 0) for x in tags}
    for i in rules:
        old = tag_dict[i.tag_id]
        tag_dict[i.tag_id] = (old[0], old[1] + 1)
    return render_template('admin/tag-manager.html', data=tag_dict.values(), rules=rules, archetypes=archetypes)


@b_admin.route('/rule-manager')
@privileges_required(['deck_mod'])
@requires_module('archetyping')
@split_database
def rule_manager(db: Database) -> str:
    tags = {x['tag_id']: DeckTag().load(x) for x in db.deck_tags.find()}
    rules = [TextDeckRule().load(x) for x in db.text_deck_rules.find().sort([
        ('tag_id', 1),
        ('rule_id', 1)
    ])]
    decks1 = [Deck().load(x) for x in db.decks.find()]
    decks = {x.rule_id: len([y for y in decks1 if x.rule_id in y.assigned_rules]) for x in rules}
    loaded_rules = [(x, tags[x.tag_id], decks[x.rule_id]) for x in rules]
    return render_template('admin/rule-manager.html', tags=tags, rules=loaded_rules)


@b_admin_api.route('/find-users', methods=['POST'])
@privileges_required(['full_admin'])
@requires_module('admin')
@split_database
def find_users(db: Database) -> Dict[str, Any]:
    req = cast(Dict[str, str], request.get_json())
    st = req['query']
    query: Dict[str, Any] = {'$or': [
        {'nickname': ireg(st)},
        {'login': ireg(st)}
    ]}
    if 'login' in req:
        query = {'$and': [query, {'login': {'$exists': 1}}]}
    try:
        ans = list(db.users.find(query))
        return {
            'items': ans,
            'success': True
        }
    except OperationFailure as e:
        return {
            'success': False,
            'reason': str(e)
        }


@b_admin_api.route('/bind-users', methods=['POST'])
@privileges_required(['full_admin'])
@requires_module('admin')
@split_database
def bind_users(db: Database) -> Response:
    req = cast(Dict[str, str], request.get_json())
    u1, u2 = req['with_login'], req['with_no_login']
    u1_obj, u2_obj = db.users.find_one({'user_id': u1}), db.users.find_one({'user_id': u2})
    if not u1_obj or not u2_obj:
        logger.warning(f'One of users {u1} and {u2} does not exist!')
        return redirect(url_for('admin.user_binding'))
    if 'login' not in u2_obj or 'nickname' in u1_obj or 'nickname' not in u2_obj:
        logger.warning('Invalid binding request!')
        return redirect(url_for('admin.user_binding'))

    db.decks.update_many({'author': u2_obj['user_id']}, {'$set': {'author': u1_obj['user_id']}})
    db.users.update_one({'user_id': u1_obj['user_id']}, {'$set': {'nickname': u2_obj['nickname']}})
    db.users.delete_one({'user_id': u2_obj['user_id']})
    return redirect(url_for('admin.user_binding'))


@b_admin_api.route('/manage-privs', methods=['POST'])
@privileges_required(['full_admin'])
@requires_module('admin')
@split_database
def manage_privileges(db: Database) -> Response:
    req = cast(Dict[str, str], request.get_json())
    uid, privs_str = req['id'], req['new_privs']
    current_user = g.actual_session['user']['user_id']
    if uid == current_user:
        logger.warning(f'Attempt to modify own privileges - {current_user}!')
        flash('Cannot modify own privileges!')
        return redirect(url_for('admin.privilege_manager'))

    user = db.users.find_one({'user_id': uid})
    if not user:
        logger.warning(f'Attempt to modify user {uid} failed - {current_user}!')
        flash(f'User {uid} does not exist!')
        return redirect(url_for('admin.privilege_manager'))
    if user['privileges']['full_admin']:
        logger.warning(f'{current_user} tried to modify admin privileges!')
        flash(f'User {uid} is a full admin!')
        return redirect(url_for('admin.privilege_manager'))

    privs = user['privileges']
    for i in privs_str.split(', '):
        privs[i] = True
    db.users.update_one({'user_id': uid}, {'$set': {'privileges': privs}})
    return redirect(url_for('admin.privilege_manager'))


@b_admin_api.route('/change-nickname', methods=['POST'])
@privileges_required(['full_admin'])
@requires_module('admin')
@split_database
def change_nickname(db: Database) -> Response:
    req = cast(Dict[str, str], request.get_json())
    uid, new_name = req['id'], req['new_name']
    user_with_name = db.users.find_one({'nickname': new_name})
    if user_with_name:
        logger.warning(f'User with name {new_name} already exists!')
        return redirect(url_for('admin.nickname_editor'))
    user = db.users.find_one({'user_id': uid})
    if not user:
        logger.warning(f'Attempt to modify user {uid} failed!')
        return redirect(url_for('admin.nickname_editor'))

    db.users.update_one({'user_id': uid}, {'$set': {'nickname': new_name}})
    return redirect(url_for('admin.nickname_editor'))


@b_admin_api.route('/create-tag', methods=['POST'])
@privileges_required(['deck_mod'])
@requires_module('archetyping')
@split_database
def create_deck_tag(db: Database) -> Response:
    req: Dict[str, str] = request.form
    tag_name, tag_desc, tag_archetype = req['tag_name'], req['tag_desc'], req['tag_archetype']
    if len(tag_name) < 3:
        flash('Tag name is too short!')
        return redirect(url_for('admin.tag_manager'))
    if tag_archetype not in archetypes:
        flash('Invalid archetype!')
        return redirect(url_for('admin.tag_manager'))

    new_tag = DeckTag()
    new_tag.name = tag_name
    new_tag.description = tag_desc
    new_tag.archetype = cast(Archetype, tag_archetype)
    db.deck_tags.insert_one(new_tag.save())

    for i in range(3):
        new_rule = TextDeckRule()
        new_rule.rule_id = new_tag.tag_id + '--' + str(i)
        new_rule.tag_id = new_tag.tag_id
        new_rule.priority = 0
        new_rule.text = ''
        db.text_deck_rules.insert_one(new_rule.save())
    return redirect(url_for('admin.tag_manager'))


@b_admin.route('/delete-tag/<tag_id>')
@privileges_required(['deck_admin'])
@requires_module('archetyping')
@split_database
def delete_deck_tag(db: Database, tag_id: str) -> Response:
    tag = db.deck_tags.find_one({'tag_id': tag_id})
    if not tag:
        flash('Invalid tag ID!')
        return redirect(url_for('admin.tag_manager'))

    first_color_rule = db.color_deck_rules.find_one({'tag_id': tag_id})
    if first_color_rule:
        flash('Cannot delete a tag with an existing color rule!')
        return redirect(url_for('admin.tag_manager'))

    first_text_rule = db.text_deck_rules.find_one({'tag_id': tag_id, 'text': {'$ne': ''}})
    if first_text_rule:
        flash('Cannot delete a tag with an existing nonempty text rule!')
        return redirect(url_for('admin.tag_manager'))

    db.deck_tags.delete_one({'tag_id': tag_id})
    return redirect(url_for('admin.tag_manager'))


@b_admin_api.route('/new-rule', methods=['POST'])
@privileges_required(['deck_mod'])
@requires_module('archetyping')
@split_database
def create_rules(db: Database) -> Response:
    req: Dict[str, str] = request.form
    tag_name = req['tag_name']
    tag_id = clean_name(tag_name)
    tag = db.deck_tags.find_one({'tag_id': tag_id})
    if not tag:
        flash('Wrong tag ID!')
        return redirect(url_for('admin.rule_manager'))

    already_existing = db.text_deck_rules.find({'tag_id': tag_id}).count()
    for i in range(3):
        new_rule = TextDeckRule()
        new_rule.rule_id = tag['tag_id'] + '--' + str(already_existing + i)
        new_rule.tag_id = tag['tag_id']
        new_rule.priority = 0
        new_rule.text = ''
        new_rule.save()
    return redirect(url_for('admin.rule_manager'))


@b_admin_api.route('/update-rule', methods=['POST'])
@privileges_required(['deck_mod'])
@requires_module('archetyping')
@split_database
def update_rule(db: Database) -> Response:
    req: Dict[str, str] = request.form
    rule_id, priority, rule_text = req['rule_id'], req['priority'], req['rule_text']

    rule = db.text_deck_rules.find_one({'rule_id': rule_id})
    if not rule:
        flash('Wrong rule ID!')
        return redirect(url_for('admin.rule_manager'))

    new_text = rule_text.replace('\r', '')
    db.text_deck_rules.update_one({'rule_id': rule_id}, {'$set': {'priority': int(priority), 'text': new_text}})
    # run_new_rules([rule]) # TODO: prime the archetyping for rule
    return redirect(url_for('admin.rule_manager'))
