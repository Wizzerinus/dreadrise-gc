from itertools import chain
from typing import Any, Callable, Dict, List, Set, Tuple

import arrow

from shared.card_enums import card_types
from shared.core_enums import Distribution
from shared.helpers.database import connect
from shared.helpers.util import clean_name, shorten_name
from shared.helpers.util2 import get_dist_constants
from shared.type_defaults import bye_user, default_deck, default_tag, get_blank_user, make_card
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag
from shared.types.set import Expansion
from shared.types.user import User

CardType = List[Tuple[Card, int]]  # [(card_name, card_count)]
CardCategory = List[Tuple[str, CardType, int]]  # [(card_type, CardType, total_count)]


class LoadedDeck:
    deck: Deck = default_deck
    card_defs: Dict[str, Card] = {}
    author: User = get_blank_user('')
    main_card: str = 'island'
    tags: List[DeckTag] = []
    sorted_cards: List[CardCategory]
    format: str = 'Unknown'
    date_str: str = '?'
    competition: Competition

    def jsonify(self) -> Dict:
        return {
            'deck': self.deck.save() if self.deck.deck_id else False,
            'card_defs': {x: y.virtual_save() for x, y in self.card_defs.items()},
            'author': self.author.save() if self.author.nickname else get_blank_user(self.deck.author).save(),
            'main_card': self.main_card,
            'name': shorten_name(self.deck.name),
            'date_str': arrow.get(self.deck.date).humanize() if self.deck else '?',
            'tags': [x.save() for x in self.tags] if self.tags else [default_tag.save()],
            'format': self.format,
            'competition': self.competition.save() if hasattr(self, 'competition') else False
        }


class PopularCardData:
    card: Card = make_card('')
    weight: int = 0
    wins: int = 0
    losses: int = 0

    def jsonify(self) -> Dict:
        return {
            'card': self.card.virtual_save() if self.card.card_id else False,
            'weight': self.weight,
            'wins': self.wins,
            'losses': self.losses
        }


class LoadedCompetition:
    competition: Competition
    decks: List[LoadedDeck] = []
    cards: Dict[str, Card] = {}
    users: Dict[str, User] = {}
    format: str = 'Unknown'
    main_card: str = 'island'
    tags: Dict[str, DeckTag] = {}
    popular_cards: List[PopularCardData] = []
    date_str: str = '?'
    deck_count: int = 0
    partial_load: bool = False

    def jsonify(self) -> Dict:
        return {
            'competition': self.competition.save() if hasattr(self, 'competition') else False,
            'decks': [x.jsonify() for x in self.decks],
            'cards': {x: y.virtual_save() for x, y in self.cards.items()},
            'users': {x: y.virtual_save() for x, y in self.users.items()},
            'main_card': self.main_card,
            'format': self.format,
            'date_str': self.date_str,
            'tags': {x: y.virtual_save() for x, y in self.tags.items()},
            'popular_cards': [x.jsonify() for x in self.popular_cards],
            'deck_count': self.deck_count,
            'partial_load': self.partial_load
        }


class SingleCardAnalysis:
    card_name: str = ''
    card_data: Card
    deck_count: int = 1
    wins: int = 0
    losses: int = 1
    winrate: float = 0
    card_count: int = 0
    average: float = 0


class SingleTypeAnalysis:
    type: str = ''
    sca: List[SingleCardAnalysis] = []
    average_count: float = 0


class DeckAnalysis:
    card_type_analysis: List[SingleTypeAnalysis] = []
    full_count: int = 1
    wins: int = 0
    losses: int = 1
    winrate: float = 0
    example_deck: LoadedDeck
    example_comp: Competition


def load_cards_from_decks(dist: Distribution, decks: List[Deck]) -> Dict[str, Card]:
    db = connect(dist)
    card_list = [x for y in decks for x in y.mainboard] + [x for y in decks for x in y.sideboard]
    return {x['name']: Card().load(x) for x in db.cards.find({'name': {'$in': card_list}})}


def sort_deck_cards(ld: LoadedDeck) -> List[CardCategory]:
    categories = [
        ['creature', 'planeswalker', 'other'],
        ['instant', 'sorcery', 'artifact', 'enchantment'],
        ['land']
    ]

    categories_loaded = []
    for arr in categories:
        arr_loaded = []
        for z in arr:
            subarr = [(ld.card_defs.get(x, make_card(x)), y) for x, y in ld.deck.mainboard.items()
                      if (x in ld.card_defs and ld.card_defs[x].main_type == z) or (
                      z == 'other' and x not in ld.card_defs)]
            if subarr:
                summ = sum([x[1] for x in subarr])
                arr_loaded.append((z.title(), subarr, summ))
        if arr_loaded:
            categories_loaded.append(arr_loaded)

    if ld.deck.sideboard:
        side = [(ld.card_defs[x], y) for x, y in ld.deck.sideboard.items() if x in ld.card_defs]
        summ = sum([x[1] for x in side])
        categories_loaded.append([('Sideboard', side, summ)])
    return categories_loaded


def load_multiple_decks(dist: Distribution, decks: List[Deck]) -> Tuple[List[LoadedDeck], Dict[str, Card]]:
    db = connect(dist)
    card_defs = load_cards_from_decks(dist, decks)
    user_ids = list({x.author for x in decks})
    users = {x['user_id']: User().load(x) for x in db.users.find({'user_id': {'$in': user_ids}})}
    tag_ids = list({x for y in decks for x in y.tags})
    all_tags = {x['tag_id']: DeckTag().load(x) for x in db.deck_tags.find({'tag_id': {'$in': tag_ids}})}
    competition_ids = list({x.competition for x in decks})
    all_competitions = {x['competition_id']: Competition().load(x)
                        for x in db.competitions.find({'competition_id': {'$in': competition_ids}})}
    constants = get_dist_constants(dist)

    lds = []
    for deck in decks:
        ld = LoadedDeck()
        ld.deck = deck
        ld.card_defs = {x: y for x, y in card_defs.items() if x in deck.mainboard or x in deck.sideboard}
        ld.author = users.get(deck.author, bye_user)
        ld.main_card = get_main_card(dist, deck, ld.card_defs)
        ld.tags = [all_tags.get(x, default_tag) for x in deck.tags]
        ld.sorted_cards = sort_deck_cards(ld)
        ld.main_card = max([(y, x) for x, y in deck.mainboard.items()
                            if x in card_defs and card_defs[x].main_type != 'land'])[1]
        ld.format = constants.format_localization.get(deck.format, 'Unknown')
        ld.date_str = arrow.get(deck.date).humanize()
        comp = all_competitions.get(deck.competition)
        if comp:
            ld.competition = comp
        lds.append(ld)

    return lds, card_defs


def load_deck_data(dist: Distribution, deck: Deck) -> LoadedDeck:
    return load_multiple_decks(dist, [deck])[0][0]


def import_deck_data(dist: Distribution, lc: LoadedCompetition, decks: List[Deck]) -> List[LoadedDeck]:
    loaded_decks: List[LoadedDeck] = []
    for i in decks:
        ld = LoadedDeck()
        ld.deck = i
        # Since this method is only called when loading a competition, we don't need a lot of these
        # ld.card_defs = {x: y for x, y in lc.cards.items() if x in i.mainboard or x in i.sideboard}
        ld.tags = [lc.tags.get(x, default_tag) for x in i.tags]
        ld.author = lc.users.get(i.author, get_blank_user(i.author))
        # ld.main_card = get_main_card(dist, i, lc.cards)
        # ld.sorted_cards = sort_deck_cards(ld)
        ld.competition = lc.competition
        loaded_decks.append(ld)
    return loaded_decks


def get_main_card(dist: Distribution, deck: Deck, card_defs: Dict[str, Card]) -> str:
    consts = get_dist_constants(dist)
    imps = [(y, x) for x, y in deck.mainboard.items() if x in card_defs and card_defs[x].main_type != 'land']
    imps += [(consts.get_sideboard_importance(card_defs[x], y), x) for x, y in deck.sideboard.items() if x in card_defs]
    if not imps:
        return 'island'
    return max(imps)[1]


def generate_popular_cards(dist: Distribution, cd: Dict[str, Card], decks: List[LoadedDeck],
                           threshold: int = 0) -> List[PopularCardData]:
    constants = get_dist_constants(dist)
    stuff = [(x, y) for z in decks for x, y in z.deck.mainboard.items() if x in cd] + \
            [(x, constants.get_sideboard_importance(cd[x], y))
             for z in decks for x, y in z.deck.sideboard.items() if x in cd]
    popularity_counter: Dict[str, int] = {}
    for card_name, card_weight in stuff:
        if cd[card_name].main_type != 'land':
            popularity_counter[card_name] = popularity_counter.get(card_name, 0) + card_weight
    all_cards = sorted([(y, x) for x, y in popularity_counter.items()], reverse=True)
    # now we limit all_cards so we never send more cards than there are decks, probably
    # well sometimes everyone will queue with a significantly different deck, so we might send slightly more
    threshold = threshold or len(decks)
    if len(all_cards) > threshold:
        last_num_to_pick = all_cards[threshold - 1][0]
        all_cards = [(y, x) for y, x in all_cards if y >= last_num_to_pick]
    # this is counterintuitive but when we generate the records, we're considering sideboard even
    # if the card is not important in sideboard
    all_data = []
    for count, card_name in all_cards:
        pcd = PopularCardData()
        pcd.card = cd[card_name]
        pcd.weight = count
        decks_with_this = [x for x in decks if card_name in x.deck.mainboard or card_name in x.deck.sideboard]
        pcd.wins = sum([x.deck.wins for x in decks_with_this])
        pcd.losses = sum([x.deck.losses for x in decks_with_this])
        all_data.append(pcd)
    return all_data


def load_competition_single(dist: Distribution, com: Competition, req_fields: Set[str] = None) -> LoadedCompetition:
    req_fields = req_fields or set()
    db = connect(dist)  # this doesn't actually create any overhead because of db caching
    lc = LoadedCompetition()
    lc.competition = com

    if 'decks' in req_fields:
        q: Dict[str, Any] = {'competition': com.competition_id}
        lc.deck_count = db.decks.count(q)
        if lc.deck_count > 250:
            min_wins = 5 if lc.deck_count > 1000 else 4
            q['wins'] = {'$gte': min_wins}
            lc.partial_load = True
        loaded_decks = [Deck().load(x) for x in db.decks.find(q)]
        if 'cards' in req_fields:
            lc.cards = load_cards_from_decks(dist, loaded_decks)
        if 'users' in req_fields:
            user_list = [x.author for x in loaded_decks]
            lc.users = {x['user_id']: User().load(x) for x in db.users.find({'user_id': {'$in': user_list}})}
        if 'tags' in req_fields:
            tag_list = [y for x in loaded_decks for y in x.tags]
            lc.tags = {x['tag_id']: DeckTag().load(x) for x in db.deck_tags.find({'tag_id': {'$in': tag_list}})}
        lc.decks = import_deck_data(dist, lc, loaded_decks)
    else:
        lc.deck_count = db.decks.count({'competition': com.competition_id})

    main_card_obj = db.competition_popularities.find_one({'competition': com.competition_id, 'format': com.format},
                                                         sort=[('true_popularity', -1)])

    constants = get_dist_constants(dist)
    lc.main_card = clean_name(main_card_obj['card_name']) if main_card_obj else constants.default_card
    lc.format = constants.format_localization.get(com.format, 'Unknown')

    lc.popular_cards = generate_popular_cards(dist, lc.cards, lc.decks) if 'cards' in req_fields else []
    lc.date_str = arrow.get(com.date).humanize()
    return lc


def load_competitions(dist: Distribution, q: dict, required_fields: Set[str] = None) -> List[LoadedCompetition]:
    db = connect(dist)
    comps = [Competition().load(x) for x in db.competitions.find(q)]
    return [load_competition_single(dist, x, required_fields) for x in comps]


def analyze(cards_to_load: List[Tuple[str, Card, List[Deck]]], attr: str = 'mainboard') -> List[SingleCardAnalysis]:
    analysises = []
    for card_name, card_def, s_decks in sorted(cards_to_load, key=lambda u: -len(u[2])):
        sca = SingleCardAnalysis()
        sca.card_name = card_name
        sca.card_data = card_def
        sca.deck_count = len(s_decks)
        sca.card_count = sum([getattr(x, attr).get(card_name, 0) for x in s_decks])
        sca.average = round(sca.card_count / sca.deck_count, 2)
        sca.wins = sum([x.wins for x in s_decks])
        sca.losses = sum([x.losses for x in s_decks])
        sca.winrate = round(sca.wins * 100 / max(1, sca.wins + sca.losses), 2)
        analysises.append(sca)
    return analysises


def get_best_deck(decks: List[Deck], deck_weight: Callable[[Deck], float]) -> Deck:
    if not decks:
        return default_deck
    max_weight = (-1.0, default_deck)
    for i in decks:
        weight = deck_weight(i)
        if weight > max_weight[0]:
            max_weight = (weight, i)
    return max_weight[1]


def load_deck_analysis(dist: Distribution, decks: List[Deck], threshold: float = 0.2) -> DeckAnalysis:
    cards = load_cards_from_decks(dist, decks)
    deck_count = len(decks)

    constants = get_dist_constants(dist)
    best_deck = get_best_deck(decks, constants.get_deck_weight)

    da = DeckAnalysis()
    if best_deck and best_deck.deck_id:
        da.example_deck = load_deck_data(dist, best_deck)
        comp = connect(dist).competitions.find_one({'competition_id': best_deck.competition})
        if comp:
            da.example_comp = Competition().load(comp)
    da.card_type_analysis = []
    for ct in chain(card_types[1:-1], ['land']):
        cards_dict = {x: (y, [z for z in decks if x in z.mainboard]) for x, y in cards.items() if y.main_type == ct}
        count_of_this = sum([z.mainboard.get(x, 0) for z in decks for x, y in cards.items() if y.main_type == ct])
        cards_to_load = [(x, y[0], y[1]) for x, y in cards_dict.items() if len(y[1]) >= deck_count * threshold]
        if cards_to_load:
            sta = SingleTypeAnalysis()
            sta.sca = analyze(cards_to_load)
            sta.type = ct.title()
            sta.average_count = round(count_of_this / len(decks), 2)
            da.card_type_analysis.append(sta)

    sb_dict = {x: (y, [z for z in decks if x in z.sideboard]) for x, y in cards.items()}
    sb_to_load = [(x, y[0], y[1]) for x, y in sb_dict.items() if len(y[1]) >= deck_count * threshold]
    if sb_to_load:
        count_of_this = sum([y for z in decks for y in z.sideboard.values()])
        sta = SingleTypeAnalysis()
        sta.sca = analyze(sb_to_load, 'sideboard')
        sta.type = 'Sideboard'
        sta.average_count = round(count_of_this / len(decks), 2)
        da.card_type_analysis.append(sta)

    da.wins = sum([x.wins for x in decks])
    da.losses = sum([x.losses for x in decks])
    da.winrate = round(da.wins * 100 / max(1, da.wins + da.losses), 2)
    da.full_count = len(decks)

    return da


def load_expansions(dist: Distribution) -> Dict[str, Expansion]:
    db = connect(dist)
    cursor = db.expansions.find({})
    return {x['code']: Expansion().load(x) for x in cursor}
