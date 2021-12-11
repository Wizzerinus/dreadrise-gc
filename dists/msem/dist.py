import logging

import click

from shared.helpers.logging import initlogger

logger = logging.getLogger('dreadrise.dist.msem')


@click.group()
def msem() -> None:
    """The distribution launcher for Dreadrise II - MSE Modern distribution."""


@msem.command()
def hello() -> None:
    """Prints Hello World message, MSEM style."""
    logger.info('Hello from MSEM!')


@msem.command()
def scrape_cards() -> None:
    """Scrape MSEM cards."""
    from .jobs.scrape_cards import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


@msem.command()
def scrape_decks() -> None:
    """Scrape MSEM cards."""
    from .jobs.scrape_decks import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


@msem.command()
def calculate_popularities() -> None:
    """Create the rules for color combinations."""
    from .jobs.calculate_popularities import run
    logger.info('Starting calculation...')
    run()
    logger.info('Calculation complete.')


if __name__ == '__main__':
    initlogger()
    msem()
