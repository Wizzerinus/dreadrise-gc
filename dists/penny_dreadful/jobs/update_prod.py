import subprocess


def run() -> None:
    """
    Update the production copy of the website.
    :return: nothing
    """
    subprocess.run(['git', 'pull'])
    subprocess.run(['pipenv', 'install'])
    venv_path = subprocess.Popen(['pipenv', '--venv'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8').strip()
    uwsgi_path = f'{venv_path}/bin/uwsgi'
    subprocess.run(['killall', uwsgi_path])
