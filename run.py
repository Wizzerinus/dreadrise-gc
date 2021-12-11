import logging

import click

from dists.run import dist
from shared.helpers.logging import initlogger
from shared.helpers.util2 import update_distributions

logger = logging.getLogger('dreadrise')


@click.group()
def runner() -> None:
    """The launcher for Dreadrise II."""


@runner.command()
@click.option('--debug/--no-debug')
def website(debug: bool) -> None:
    """Start the website."""
    from website import run
    update_distributions()
    logger.info('Starting the website...')
    run(debug)
    logger.info('Website stopped.')


runner.add_command(dist)


if __name__ == '__main__':
    initlogger()
    runner()
