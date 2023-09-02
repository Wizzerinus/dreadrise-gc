import logging
from collections import Counter
from typing import Dict, Iterable, List, Tuple

from shared.card_enums import format_popularity, popularity_multiplier
from shared.types.caching import CompetitionPopularity, DeckTagPopularity, FormatPopularity, Popularity
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag

logger = logging.getLogger('dreadrise.popularity')


def count(decks: List[Deck], cards: Dict[str, Card]) -> Dict[str, float]:
    card_counts: Dict[str, int] = Counter()
    for i in decks:
        if i.competition:
            for j, c in i.mainboard.items():
                if j in cards and cards[j].main_type != 'land':
                    card_counts[j] += c * (i.wins * 2 + i.losses + 1)
    max_popularity = max(card_counts.values()) + 1 if len(card_counts) > 0 else 1
    return {x: c / max_popularity for x, c in card_counts.items()}


def run_popularity(fmt: str, all_cards: Dict[str, Card], all_decks: List[Deck], all_competitions: List[Competition],
                   all_tags: List[DeckTag]) -> \
        Tuple[List[CompetitionPopularity], List[DeckTagPopularity], Popularity, Dict[str, str]]:
    decks_from_format = [x for x in all_decks if x.format == fmt] if fmt != '_all' else all_decks
    all_format_popularities = count(all_decks, all_cards)
    card_popularities = count(decks_from_format, all_cards)

    nonland_cards = {x for x, y in all_cards.items() if y.main_type != 'land'}
    basics = {x for x, y in all_cards.items() if 'Basic' not in y.types}

    comp_pop: List[CompetitionPopularity] = []
    dt_pop: List[DeckTagPopularity] = []
    for i in all_competitions:
        decks = [x for x in decks_from_format if x.competition == i.competition_id]
        if not decks:
            continue

        counter = count(decks, all_cards)
        for c, val in sorted(counter.items(), key=lambda x: card_popularities[x[0]] * popularity_multiplier - x[1])[:3]:
            cp = CompetitionPopularity()
            cp.format = fmt
            cp.card_name = c
            cp.self_popularity = val
            cp.total_popularity = card_popularities[c]
            cp.competition = i.competition_id
            cp.preprocess()
            comp_pop.append(cp)

    for j in all_tags:
        decks = [x for x in decks_from_format if j.tag_id in x.tags]
        if not decks:
            continue

        counter = count(decks, all_cards)
        for c, val in sorted(counter.items(), key=lambda x: card_popularities[x[0]] * popularity_multiplier - x[1])[:3]:
            dtp = DeckTagPopularity()
            dtp.format = fmt
            dtp.card_name = c
            dtp.self_popularity = val
            dtp.total_popularity = card_popularities[c]
            dtp.deck_tag = j.tag_id
            dtp.preprocess()
            dt_pop.append(dtp)

    if fmt == '_all' or not card_popularities:
        fp = Popularity()
    else:
        c, val = min(card_popularities.items(), key=lambda x: all_format_popularities[x[0]] * format_popularity - x[1])
        fp = FormatPopularity()
        fp.format = fmt
        fp.card_name = c
        fp.self_popularity = val
        fp.total_popularity = card_popularities[c]
        fp.true_popularity = fp.self_popularity - fp.total_popularity
        fp.deck_count = len(decks_from_format)

    top_cards_per_id = {}
    if fmt != '_all':
        for k in decks_from_format:
            nonland_cards_lst: Iterable[Tuple[str, int]] = [x for x in k.mainboard.items() if x[0] in nonland_cards]
            if nonland_cards_lst:
                top_cards_per_id[k.deck_id] = max(
                    nonland_cards_lst, key=lambda u: u[1] / 2 - card_popularities[u[0]])[0]
            elif k.mainboard:
                logger.warning(f'Deck with only lands: {k.deck_id} ({k.name})')
                top_cards_per_id[k.deck_id] = max(
                    k.mainboard.items(), key=lambda u: (100 if u[0] not in basics else 0) + u[1])[0]
            else:
                logger.warning(f'Deck with empty mainboard: {k.deck_id} ({k.name})')

    return comp_pop, dt_pop, fp, top_cards_per_id
