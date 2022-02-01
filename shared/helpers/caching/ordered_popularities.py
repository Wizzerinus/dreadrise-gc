import logging
import traceback
from typing import Callable, List

from pymongo.database import Database

from shared.helpers.caching.playability import run_playability
from shared.helpers.caching.popularity import run_popularity
from shared.helpers.caching.tag_covers import run_tag_covers
from shared.helpers.exceptions import DreadriseError
from shared.types.caching import CardPlayability
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag

logger = logging.getLogger('dreadrise.popularity')


def run_ordered_popularities(client: Database, postprocess_playability: Callable[[CardPlayability, str, int], None],
                             format_order: List[str], formats: List[str]) -> None:
    """
    Calculate the popularity of various cards with ordered formats.
    :return: nothing
    """
    try:
        logger.info('Loading data...')
        all_card_iter = (Card().load(x) for x in client.cards.find())
        all_cards = {x.name: x for x in all_card_iter}
        logger.info(f'Loaded {len(all_cards)} cards.')
        all_competitions = [Competition().load(x) for x in client.competitions.find()]
        logger.info(f'Loaded {len(all_competitions)} competitions.')
        all_tags = [DeckTag().load(x) for x in client.deck_tags.find()]
        logger.info(f'Loaded {len(all_tags)} deck tags.')
        all_decks = [Deck().load(x) for x in client.decks.find()]
        logger.info(f'Loaded {len(all_decks)} decks.')
        logger.info('Loaded data!')

        logger.warning('Dropping collections')
        query = {'format': {'$in': formats}}
        client.competition_popularities.delete_many(query)
        client.tag_popularities.delete_many(query)
        client.format_popularities.delete_many(query)
        client.archetype_cache.delete_many(query)
        client.card_playability.delete_many(query)

        format_counts = {x: len([y for y in all_decks if y.format == x or x == '_all']) for x in formats}
        for x in formats:
            if format_counts[x]:
                logger.warning(f'Processing format {x}')

                expected_formats = []
                for i in format_order:  # if x is not in format_order, then it just uses every format, like _all
                    expected_formats.append(i)
                    if i == x:
                        break
                logger.info(f'Found {len(expected_formats)} formats before this one, getting the list of decks...')
                local_decks = [x for x in all_decks if x.format in expected_formats]
                logger.info(f'Found {len(local_decks)} decks')

                logger.info('Calculating popularities...')
                comp_pop, dt_pop, f_pop = run_popularity(x, all_cards, local_decks, all_competitions, all_tags)
                logger.info(f'Calculated {len(comp_pop)} popularity entries for competitions, {len(dt_pop)} for tags')

                logger.info('Inserting popularities...')
                client.competition_popularities.insert_many([y.save() for y in comp_pop])
                client.tag_popularities.insert_many([y.save() for y in dt_pop])
                if len(format_order) > 1 and x != '_all':
                    client.format_popularities.insert_one(f_pop.save())
                logger.info('Insert complete.')

                logger.info('Calculating tag covers...')
                arch_cache = run_tag_covers(x, local_decks, all_tags, dt_pop)
                logger.info(f'Calculated {len(arch_cache)} tag covers')

                logger.info('Inserting archetypes...')
                client.archetype_cache.insert_many([y.save() for y in arch_cache])
                logger.info('Insert complete.')

                logger.info('Calculating staples cache...')
                staple_cache = run_playability(x, all_cards, local_decks)
                for j in staple_cache:
                    postprocess_playability(j, x, format_counts[x])
                logger.info(f'Calculated {len(staple_cache)} staples entries')

                if len(staple_cache) > 0:
                    logger.info('Inserting staples...')
                    client.card_playability.insert_many([y.save() for y in staple_cache])
                    logger.info('Insert complete.')
                else:
                    logger.info('Staples not detected.')
            else:
                logger.info(f'Skipping format {x}')

    except (DreadriseError, KeyError, ValueError):
        logger.error('A error occured!')
        traceback.print_exc()
