# -*- coding: utf-8 -*-

import click

from src.commands.pipelines import Pipeline


@click.group(chain=True)
@click.option('--file', '-f', type=click.Path(), help='Config file "django.json"')
def main(file):
    click.echo("\nStarting...")


@main.command()
def deploy():
    Pipeline.deploy()


@main.command()
def deps():
    Pipeline.deps()


@main.command()
def update():
    Pipeline.update()


@main.command()
def install():
    Pipeline.setup_server()


@main.command()
def uninstall():
    Pipeline.clean_server()


@main.command()
def fix_permissions():
    Pipeline.fix_permissions()


@main.command()
def add_remote():
    Pipeline.add_remote()


@main.command()
def upload_key():
    Pipeline.upload_sshkey()


@main.command()
def create_superuser():
    Pipeline.createsuperuser()


@main.command()
def resetdb():
    Pipeline.reset_db()


@main.command()
@click.argument('artifact')
def setup_ssl(artifact):
    Pipeline.setup_ssl(artifact=artifact)


@main.command()
def restart():
    Pipeline.restart_server()


@main.command()
@click.argument('command')
def run(command):
    Pipeline.run_command(command=command)


@main.command()
def check_language():
    Pipeline.server_language()

