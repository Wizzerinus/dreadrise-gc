import logging
import traceback
from typing import Callable, Optional, Dict

from pymongo.database import Database

from shared.helpers.exceptions import DreadriseError
from shared.types.caching import CardPlayability
from shared.types.card import Card
from shared.types.competition import Competition
from shared.types.deck import Deck
from shared.types.deck_tag import DeckTag

from .playability import run_playability
from .popularity import run_popularity
from .tag_covers import run_tag_covers

logger = logging.getLogger('dreadrise.popularity')


def run_all_popularities(client: Database, postprocess_playability: Callable[[CardPlayability, str, int], None],
                         time_check: Callable[[Deck], bool] = lambda a: True,
                         card_cache: Optional[Dict[str, Card]] = None) -> None:
    """
    Calculate the popularity of various cards.
    :return: nothing
    """
    try:
        logger.info('Loading data...')

        if card_cache:
            all_cards = card_cache
        else:
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
        client.competition_popularities.delete_many({})
        client.tag_popularities.delete_many({})
        client.format_popularities.delete_many({})
        client.archetype_cache.delete_many({})
        client.card_playability.delete_many({})

        formats = {x.format for x in all_competitions}
        formats.add('_all')  # does not really matter if there's 1 format only
        format_counts = {x: len([y for y in all_decks if y.format == x or x == '_all']) for x in formats}
        for x in formats:
            if format_counts[x]:
                logger.warning(f'Processing format {x}')

                logger.info('Calculating popularities...')
                comp_pop, dt_pop, f_pop = run_popularity(x, all_cards, all_decks, all_competitions, all_tags)
                logger.info(f'Calculated {len(comp_pop)} popularity entries for competitions, {len(dt_pop)} for tags')

                logger.info('Inserting popularities...')
                client.competition_popularities.insert_many([y.save() for y in comp_pop])
                client.tag_popularities.insert_many([y.save() for y in dt_pop])
                if len(formats) > 1 and x != '_all':
                    client.format_popularities.insert_one(f_pop.save())
                logger.info('Insert complete.')

                logger.info('Calculating tag covers...')
                arch_cache = run_tag_covers(x, all_decks, all_tags, dt_pop)
                logger.info(f'Calculated {len(arch_cache)} tag covers')

                logger.info('Inserting archetypes...')
                client.archetype_cache.insert_many([y.save() for y in arch_cache])
                logger.info('Insert complete.')

                logger.info('Calculating staples cache...')
                staple_cache = run_playability(x, all_cards, [y for y in all_decks if time_check(y)])
                for i in staple_cache:
                    postprocess_playability(i, x, format_counts[x])
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
