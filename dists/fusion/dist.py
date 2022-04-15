import logging

import click

from shared.helpers.logging import initlogger

logger = logging.getLogger('dreadrise.dist.fusion')


@click.group()
def fusion() -> None:
    """The distribution launcher for Dreadrise II - Fusion distribution."""


@fusion.command()
def hello() -> None:
    """Print Hello World message, Fusion style."""
    logger.info('Hello from Fusion!')


@fusion.command()
def scrape_cards() -> None:
    """Scrape cards from the PD and MSEM databases."""
    from .jobs.scrape_cards import run
    logger.info('Starting scrape process...')
    run()
    logger.info('Scraping complete.')


if __name__ == '__main__':
    initlogger()
    fusion()
