import logging

import click

from shared.helpers.logging import initlogger

logger = logging.getLogger('dreadrise.dist.pd')


@click.group()
def pd() -> None:
    """The distribution launcher for Dreadrise II - Penny Dreadful distribution."""


@pd.command()
def hello() -> None:
    """Prints Hello World message, PD style."""
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
def scrape_all_decks() -> None:
    """Scrape decks from the PD API."""
    from .jobs.scrape_decks import run_all_seasons
    logger.info('Running all seasons...')
    run_all_seasons()
    logger.info('Scraping complete.')


@pd.command()
def generate_format() -> None:
    """Cache the PD legality lists."""
    from .jobs.generate_format import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


@pd.command()
def calculate_popularities() -> None:
    """Create the rules for color combinations."""
    from .jobs.calculate_popularities import run
    logger.info('Starting calculation...')
    run()
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
