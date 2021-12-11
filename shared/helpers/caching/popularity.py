from collections import Counter
from typing import Dict, List, Tuple

from shared.card_enums import format_popularity, popularity_multiplier
from shared.types.caching import CompetitionPopularity, DeckTagPopularity, FormatPopularity, Popularity
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag


def count(decks: List[Deck], cards: Dict[str, Card]) -> Dict[str, float]:
    card_counts: Dict[str, int] = Counter()
    for i in decks:
        if i.wins > 0 or i.losses > 0:
            for j, c in i.mainboard.items():
                if j in cards and cards[j].main_type != 'land':
                    card_counts[j] += c * (i.wins * 2 + i.losses)
    max_popularity = max(card_counts.values()) + 1 if len(card_counts) > 0 else 1
    return {x: c / max_popularity for x, c in card_counts.items()}


def run_popularity(fmt: str, all_cards: Dict[str, Card], all_decks: List[Deck], all_competitions: List[Competition],
                   all_tags: List[DeckTag]) -> \
        Tuple[List[CompetitionPopularity], List[DeckTagPopularity], Popularity]:
    decks_from_format = [x for x in all_decks if x.format == fmt] if fmt != '_all' else all_decks
    all_format_popularities = count(all_decks, all_cards)
    card_popularities = count(decks_from_format, all_cards)

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

    if fmt == '_all':
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

    return comp_pop, dt_pop, fp
