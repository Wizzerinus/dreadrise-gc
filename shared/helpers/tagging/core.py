import logging
from typing import Any, Iterable, Sequence

from pymongo import UpdateOne

from shared.core_enums import Distribution
from shared.helpers.database import connect
from shared.helpers.db_loader import load_cards_from_decks
from shared.helpers.util2 import get_dist_constants
from shared.types.card import Card
from shared.types.deck import Deck
from shared.types.deck_tag import ColorDeckRule, DeckRule, DeckTag, TextDeckRule

logger = logging.getLogger('dreadrise.tagging.core')

MaybeCC = dict[str, Card] | None


def run(dist: Distribution, rules: Iterable[DeckRule], q: Iterable[Deck], card_cache: MaybeCC = None) -> MaybeCC:
    constants = get_dist_constants(dist)
    if 'archetyping' not in constants.EnabledModules:
        logger.warning(f'Distribution {dist} does not support tags')
        return None

    db = connect(dist)
    logger.info('Loading tags')
    tags = {x['tag_id']: DeckTag().load(x) for x in db.deck_tags.find()}
    logger.info(f'{len(tags)} tags loaded')
    rule_list = list(rules)
    decks = list(q)

    need_to_load_cards = len([x for x in rule_list if isinstance(x, ColorDeckRule)]) > 0
    cards = card_cache or (load_cards_from_decks(dist, decks) if need_to_load_cards else {})
    rule_set = {x.rule_id for x in rule_list}
    full_text_rule_dict = {x['rule_id']: TextDeckRule().load(x) for x in db.text_deck_rules.find()}
    full_rule_dict: dict[str, DeckRule] = {x['rule_id']: ColorDeckRule().load(x) for x in db.color_deck_rules.find()}
    logger.info(f'{len(full_text_rule_dict)} text and {len(full_rule_dict)} color rules loaded')
    full_rule_dict.update(full_text_rule_dict)
    logger.info(f'{len(full_rule_dict)} rules loaded')

    actions = []
    for deck in decks:
        logger.debug(f'Deck {deck.name}')
        assigned_rules: list[str] = list(set([x for x in deck.assigned_rules if x not in rule_set and
                                              x in full_rule_dict]))
        assigned_existing_rules = {x for x in deck.assigned_rules if x in rule_set}

        action_done = False
        for rule in rule_list:
            applies = rule.applies_to(deck, cards)
            if (applies and rule.rule_id not in assigned_rules) or \
                    (not applies and rule.rule_id in assigned_existing_rules):
                action_done = True
            if applies:
                assigned_rules.append(rule.rule_id)
            # logger.debug(f'Deck: {deck.name} rule: {rule.id} applies: {applies} '
            #             f'has_rule: {rule.rule_id in assigned_rules}')

        if not action_done:
            continue
        logger.debug(assigned_rules)

        action: dict[str, Any] = {}
        assigned_rules.sort(key=lambda x: -full_rule_dict[x].priority)
        deck.tags = []
        for r in assigned_rules:
            if full_rule_dict[r].tag_id not in deck.tags:
                deck.tags.append(full_rule_dict[r].tag_id)

        action['assigned_rules'] = assigned_rules
        action['tags'] = deck.tags

        if not deck.name or deck.is_name_placeholder:
            logger.warning('Setting the name automatically')
            tag_name = tags[deck.tags[0]].name.replace('Color: ', '')
            new_name = f'{deck.author[0:3]}\'s {tag_name}'
            action['name'] = new_name
            logger.debug(f'New name: {new_name}')
        action['is_sorted'] = True

        logger.debug('Rules: %s', action['assigned_rules'])
        logger.debug('Tags: %s', action['tags'])
        actions.append(UpdateOne({'deck_id': deck.deck_id}, {'$set': action}))
    logger.warning(f'Generated {len(actions)} actions')
    if actions:
        db.decks.bulk_write(actions)
    logger.warning('Sorting complete.')
    return cards or None


def run_new_rules(dist: Distribution, rules: Sequence[DeckRule], card_cache: MaybeCC = None) -> MaybeCC:
    db = connect(dist)
    logger.debug('Running the checker for new rules.')
    logger.debug(f'Found {len(rules)} rules.')
    return run(dist, rules, (Deck().load(x) for x in db.decks.find()), card_cache=card_cache)


def run_new_decks(dist: Distribution, card_cache: MaybeCC = None) -> MaybeCC:
    db = connect(dist)
    logger.debug('Running the checker for new decks.')
    tdr: list[DeckRule] = [TextDeckRule().load(x) for x in db.text_deck_rules.find()]
    tdr += [ColorDeckRule().load(x) for x in db.color_deck_rules.find()]
    logger.debug(f'Found {len(tdr)} rules.')
    return run(dist, tdr, (Deck().load(x) for x in db.decks.find({'is_sorted': False})), card_cache=card_cache)


def run_all_decks(dist: Distribution, card_cache: MaybeCC = None) -> MaybeCC:
    db = connect(dist)
    logger.debug('Running the checker for all decks.')
    tdr: list[DeckRule] = [TextDeckRule().load(x) for x in db.text_deck_rules.find()]
    tdr += [ColorDeckRule().load(x) for x in db.color_deck_rules.find()]
    logger.debug(f'Found {len(tdr)} rules.')
    return run(dist, tdr, (Deck().load(x) for x in db.decks.find()), card_cache=card_cache)
