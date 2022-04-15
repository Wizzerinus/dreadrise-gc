import logging

import click

from shared.core_enums import distribution_rollback
from shared.helpers.logging import initlogger
from shared.helpers.migration import run_migration

from .fusion.dist import fusion
from .msem.dist import msem
from .penny_dreadful.dist import pd

logger = logging.getLogger('dreadrise.dist')


@click.group()
def dist() -> None:
    """The distribution launcher for Dreadrise II."""


@dist.command()
@click.argument('distrib')
def migrate(distrib: str) -> None:
    if distrib not in distribution_rollback:
        logger.error(f'Unknown distribution: {distrib}')
        return
    distd = distribution_rollback[distrib]

    logger.info(f'Migrating distribution {distd}...')
    run_migration(distd)


dist.add_command(msem)
dist.add_command(pd)
dist.add_command(fusion)


if __name__ == '__main__':
    initlogger()
    dist()
