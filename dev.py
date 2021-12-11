import subprocess
import sys

import click


@click.group()
def cli() -> None:
    """The development hub for Dreadrise II."""


@cli.command()
def flake8() -> int:
    """Run the linter."""
    print('Running flake8...')
    from flake8.api import legacy
    style = legacy.get_style_guide()
    report = style.check_files(['dists', 'shared', 'website'])
    if not report.get_statistics('E'):
        print('flake8 succeeded')
        return 0
    else:
        print('flake8 failed')
        return 1


@cli.command()
def mypy() -> int:
    """Run the type checker."""
    print('Running mypy...')
    from mypy.api import run
    stdout, stderr, e = run(['dists', 'shared', 'website'])
    errors = [x for x in stdout.split('\n') if ' error:' in x and 'found module but no type hints' not in x and
              'stubs not installed' not in x]

    if errors:
        print(f'mypy failed with error {e}')
        print('\n'.join(errors))
        return e
    else:
        print('mypy succeeded')
        return 0


@cli.command()
def check():
    """Run the code checkers."""
    print('Checking code...')
    f8 = flake8.callback()
    mp = mypy.callback()
    if f8 or mp:
        print('The checkers errored.')
        sys.exit(1)


@cli.command()
def isort():
    """Sort imports."""
    print('Running isort...')
    from isort import Config, file, files
    for i in files.find(['dists', 'shared', 'website', 'dev.py', 'run.py'], Config(), [], []):
        file(i)
    print('isort finished')


@cli.command()
def complete():
    """Sort imports and check the code."""
    print('Sorting imports...')
    isort.callback()
    check.callback()


@cli.command()
def tarball():
    """Create a tarball."""
    print('Creating code tarball...')
    subprocess.run(['git', 'archive', 'master', '-o', 'code.tar.gz'])
    print('Creating secrets tarball...')
    subprocess.run(['tar', '-czf', 'secrets.tar.gz', 'launcher.wsgi', 'config/secrets.yml',
                    'config/dist/msem/secrets.yml', 'config/dist/penny_dreadful/secrets.yml'])


if __name__ == '__main__':
    cli()
