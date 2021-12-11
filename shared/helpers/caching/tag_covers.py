import logging
from typing import Dict, List, Tuple

from shared.types.caching import DeckTagCache, DeckTagPopularity
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag

logger = logging.getLogger('dreadrise.popularity.tags')


def run_tag_covers(fmt: str, dck: List[Deck], tags: List[DeckTag], pops: List[DeckTagPopularity]) -> List[DeckTagCache]:
    decks_in_format = [x for x in dck if x.format == fmt] if fmt != '_all' else dck
    tag_dict = {x.tag_id: x for x in tags}
    card_stuff = [(z.tags[0], z.wins, z.losses) for z in decks_in_format if z.tags]
    counter: Dict[str, DeckTagCache] = {}
    wins_losses: Dict[str, Tuple[int, int]] = {}
    for tag_id, wins, losses in card_stuff:
        dtc = counter.get(tag_id, None)
        if not dtc:
            dtc = DeckTagCache()
            dtc.format = fmt
            dtc.tag = tag_id
            dtc.tag_name = tag_dict[tag_id].name
            dtc.cards = [x.card_name for x in pops if x.deck_tag == tag_id]
            dtc.deck_count = 0
            counter[tag_id] = dtc

        dtc.deck_count += 1
        wl = wins_losses.get(tag_id, (0, 0))
        wins_losses[tag_id] = (wl[0] + wins, wl[1] + losses)

    ans = []
    for name, dtc in counter.items():
        dtc.deck_wins, dtc.deck_losses = wins_losses[name]
        if dtc.cards:
            dtc.clean()
            ans.append(dtc)
        else:
            logger.warning(f'Skipping archetype {name}')

    return ans
