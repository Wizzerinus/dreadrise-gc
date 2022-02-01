import subprocess

from shared.helpers import configuration


def run() -> None:
    """
    Update the production copy of the website.
    :return: nothing
    """
    rl = configuration.get('repo_location')
    subprocess.Popen(['git', 'pull'], cwd=rl)
