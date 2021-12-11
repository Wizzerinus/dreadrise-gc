from typing import List, Tuple

from plotly import graph_objects as pgo
from pymongo.database import Database

from shared.card_enums import archetypes
from shared.type_defaults import default_tag
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag


def calculate_winrate(decks: List[Deck]) -> float:
    wins = sum([x.wins for x in decks])
    losses = sum([x.losses for x in decks])
    if wins + losses > 0:
        return wins / (wins + losses)
    return -1


def interpolate(num: float, breakpoints: List[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    single_percentage = 1 / (len(breakpoints) - 1)
    segment_num = int(num / single_percentage)
    if segment_num == len(breakpoints) - 1:
        return breakpoints[-1]
    b1, b2 = breakpoints[segment_num], breakpoints[segment_num + 1]
    time_diff = (num - single_percentage * segment_num) * (len(breakpoints) - 1)
    return (
        int(b1[0] * (1 - time_diff) + b2[0] * time_diff),
        int(b1[1] * (1 - time_diff) + b2[1] * time_diff),
        int(b1[2] * (1 - time_diff) + b2[2] * time_diff),
    )


def calculate_winrate_color(wr: float) -> str:
    if wr < 0:
        return '#999999'
    breakpoints = [
        (255, 16, 16),
        (204, 128, 16),
        (204, 204, 16),
        (16, 204, 16),
        (16, 16, 204)
    ]
    color = interpolate(wr, breakpoints)
    return '#' + ''.join([f'{x:X}' for x in color])


def metagame_breakdown(db: Database, decks: List[Deck], winrate_colors: bool = True) -> pgo.Figure:
    required_tags = list({x.tags[0] if x.tags else '' for x in decks})
    # loaded_tags = {x.tag_id: x for x in DeckTag.objects(tag_id__in=required_tags)}
    loaded_tags = {x['tag_id']: DeckTag().load(x) for x in db.deck_tags.find({'tag_id': {'$in': required_tags}})}
    loaded_tags['unknown'] = default_tag
    for d in decks:
        if not d.tags:
            d.tags = ['unknown']

    tag_counts = [(len([y for y in decks if y.tags[0] == x]), x) for x in required_tags]
    sorted_tag_counts = sorted(tag_counts, reverse=True)
    if len(sorted_tag_counts) < 10:
        min_decks = 1
    else:
        min_decks = sorted_tag_counts[9][0]

    data: List[Tuple[str, str, int, str, str]] = []
    for i in archetypes:
        with_this_archetype = [x for x in decks if loaded_tags[x.tags[0]].archetype == i]
        if not with_this_archetype:
            continue
        arch_name = i.title()
        wr = calculate_winrate(with_this_archetype)
        wr_str = str(round(wr * 100, 2)) + '% winrate'
        data.append((arch_name, '', len(with_this_archetype), wr_str, calculate_winrate_color(wr)))

        if i != 'unclassified':
            tags_with_this_archetype = [x for x in loaded_tags.values() if x.archetype == i]
            for j in tags_with_this_archetype:
                with_this_tag = [x for x in decks if x.tags[0] == j.tag_id]
                if len(with_this_tag) < min_decks:
                    continue
                if j.name != arch_name:
                    wr = calculate_winrate(with_this_tag)
                    wr_str = str(round(wr * 100, 2)) + '% winrate'
                    data.append((j.name, arch_name, len(with_this_tag), wr_str, calculate_winrate_color(wr)))

    dict_data = {
        'labels': [x[0] for x in data],
        'parents': [x[1] for x in data],
        'values': [x[2] for x in data],
    }
    if winrate_colors:
        dict_data['hovertext'] = [x[3] for x in data]
        dict_data['marker'] = {'colors': [x[4] for x in data]}
    # fig = px.sunburst(dict_data, names='tag', parents='parent', values='value')
    fig = pgo.Figure(pgo.Sunburst(dict_data, branchvalues='total'))
    fig.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0})
    return fig
