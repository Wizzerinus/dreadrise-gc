import logging

import pyparsing as pp
import pyparsing.exceptions

from shared.types.deck import Deck

logger = logging.getLogger('dreadrise.tagging.text')
comparisons = ['>', '<', '>=', '<=', '=']


def _get_parser() -> pp.ParserElement:
    letters = pp.alphanums + '\'-, /'
    card_name = pp.Word(letters)
    card_target_base = pp.Literal('side') | pp.Literal('*')
    card_target = pp.ZeroOrMore(card_target_base + pp.Literal('.').suppress())
    card_def = card_target + card_name
    multiple_card_names = card_def + pp.ZeroOrMore(pp.Literal('+').suppress() + card_def)
    comparison = pp.one_of(' '.join(comparisons))
    number = pp.Word(pp.nums).set_parse_action(lambda t: int(t[0]))
    return multiple_card_names + comparison + number


def compile_rule(rule: str) -> list:
    if not rule:
        return []

    parser = _get_parser()
    try:
        return [parser.parse_string(x) for x in rule.split('\n')]
    except pyparsing.exceptions.ParseException as e:
        logger.error('Error while running text rules: %s - %s!', rule, e.msg)
        return []


def text_rule_applies(d: Deck, compiled_rule: list) -> bool:
    """
    Check whether a text rule applies to a deck.
    The rule should be formatted as:
    <card_a> + <card_b> + <card_c> >= (= <= > <) (number)
    each card is either [Card name] for maindeck, side.[Card name] for sideboard, or *.[Card name] for any.
    :param d: the deck
    :param compiled_rule: the rule compiled from one with the rules above
    :return: true if applies, false otherwise
    """
    if not compiled_rule:
        return False

    for i in compiled_rule:
        current_sum = 0
        current_mode = -1
        comp = ''
        for j in i:
            if j == '*':
                current_mode = 0
            elif j == 'side':
                current_mode = 1
            elif isinstance(j, str) and j not in comparisons:
                j = j.strip()
                current_sum += (d.mainboard.get(j, 0) if current_mode <= 0 else 0)
                current_sum += (d.sideboard.get(j, 0) if current_mode >= 0 else 0)
                current_mode = -1
            elif j in comparisons:
                comp = j
            elif not comp:
                return False
            else:
                if (comp == '=' and current_sum != j) or (comp == '>' and current_sum <= j) or \
                        (comp == '>=' and current_sum < j) or (comp == '<' and current_sum >= j) or \
                        (comp == '<=' and current_sum > j):
                    return False
    return True
