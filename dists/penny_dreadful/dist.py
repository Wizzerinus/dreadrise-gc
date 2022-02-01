import logging

import click

from shared.helpers.logging import initlogger

logger = logging.getLogger('dreadrise.dist.pd')


@click.group()
def pd() -> None:
    """The distribution launcher for Dreadrise II - Penny Dreadful distribution."""


@pd.command()
def hello() -> None:
    """Print Hello World message, PD style."""
    logger.info('Hello from PD!')


@pd.command()
def scrape_cards() -> None:
    """Scrape cards from scryfall."""
    from .jobs.scrape_cards import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


@pd.command()
def scrape_archetypes() -> None:
    """Scrape archetypes from the PD API."""
    from .jobs.scrape_decks import run_archetypes
    logger.info('Starting scrape process...')
    run_archetypes()
    logger.info('Scraping complete.')


@pd.command()
@click.argument('season_num')
def scrape_decks(season_num: str) -> None:
    """Scrape decks from the PD API."""
    from .jobs.scrape_decks import run_all_decks
    logger.info('Starting scrape process...')
    run_all_decks(season_num)
    logger.info('Scraping complete.')


@pd.command()
def scrape_last_season() -> None:
    """Scrape decks from the PD API."""
    from .jobs.scrape_decks import run_last_season
    logger.info('Starting scrape process...')
    run_last_season()
    logger.info('Scraping complete.')


@pd.command()
def full_update() -> None:
    """Scrape archetypes from the PD API, decks from the PD API, and recalculate the popularities."""
    scrape_archetypes.callback()  # type: ignore
    scrape_last_season.callback()  # type: ignore
    calculate_ls_popularities.callback()  # type: ignore


@pd.command()
@click.argument('first_season_num')
def scrape_all_decks(first_season_num: str) -> None:
    """Scrape decks from the PD API."""
    from .jobs.scrape_decks import run_all_seasons
    logger.info('Running all seasons...')
    run_all_seasons(int(first_season_num))
    logger.info('Scraping complete.')


@pd.command()
def generate_format() -> None:
    """Cache the PD legality lists."""
    from .jobs.generate_format import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


@pd.command()
def prepare_rotation() -> None:
    """Load the new season data and change the card database based on it."""
    generate_format.callback()  # type: ignore
    scrape_cards.callback()  # type: ignore


@pd.command()
def full_recalculate_popularities() -> None:
    """Create the rules for color combinations."""
    from .jobs.calculate_popularities import run_all_seasons
    logger.info('Starting calculation...')
    run_all_seasons()
    logger.info('Calculation complete.')


@pd.command()
def calculate_ls_popularities() -> None:
    """Create the rules for color combinations."""
    from .jobs.calculate_popularities import run_single_season
    logger.info('Starting calculation...')
    run_single_season()
    logger.info('Calculation complete.')


@pd.command()
def update_deck_sources() -> None:
    """Update the deck sources for decks without one."""
    from .jobs.update_deck_sources import run
    logger.info('Starting calculation...')
    run()
    logger.info('Calculation complete.')


if __name__ == '__main__':
    initlogger()
    pd()
