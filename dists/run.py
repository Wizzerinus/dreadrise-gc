import logging

import click

from shared.helpers.logging import initlogger

from .msem.dist import msem
from .penny_dreadful.dist import pd

logger = logging.getLogger('dreadrise.dist')


@click.group()
def dist() -> None:
    """The distribution launcher for Dreadrise II."""


dist.add_command(msem)
dist.add_command(pd)


if __name__ == '__main__':
    initlogger()
    dist()
