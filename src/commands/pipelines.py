# -*- coding: utf-8 -*-


import click

from src.commands.project import Project
from src.commands.server import Server
from src.commands.config import WebServer
from src.common.context import CommandContext
from src.common.decorators import settings, update_config_file


class Pipeline:

    @staticmethod
    @settings(allow_sudo=True)
    def update(context: CommandContext):
        context.connection.sudo('apt-get update')
        context.connection.sudo('apt-get upgrade -y')

    @staticmethod
    @settings(allow_sudo=True)
    def deps(context: CommandContext):
        Server.deps(context)

    @staticmethod
    @settings(allow_sudo=True)
    def setup_server(context: CommandContext):
        Server.deps(context)
        Server.user(context)
        Server.group(context)
        Server.layout(context)
        Server.create_db(context)
        Server.fix_permissions(context)
        Server.git(context)
        Server.add_remote(context)
        Server.web_server(context)
        Server.gunicorn(context)
        Server.supervisor(context)
        Server.fix_permissions(context)
        Server.letsencrypt(context)

    @staticmethod
    @settings(allow_sudo=True)
    def clean_server(context: CommandContext):
        """
        Uninstall app in selected server(s)
        """
        Server.clean(context)

    @staticmethod
    @settings(allow_sudo=True)
    def restart_server(context: CommandContext):
        """
        Restart all app services.
        """
        Server.restart_services(context)

    @staticmethod
    @settings()
    def deploy(context: CommandContext):
        Project.push(context)
        Project.environment(context)
        Project.install(context)
        Project.clean(context)

    @staticmethod
    @settings(allow_sudo=True)
    def fix_permissions(context: CommandContext):
        Server.fix_permissions(context)

    @staticmethod
    @settings()
    def add_remote(context: CommandContext):
        Server.add_remote(context)

    @staticmethod
    @settings(allow_sudo=True)
    def createsuperuser(context: CommandContext):
        """
        Create a project superuser in selected server(s).
        """
        Project.create_superuser(context)

    @staticmethod
    @settings()
    def run_command(context: CommandContext, command):
        Project.run_command(context, command)

    @staticmethod
    @settings()
    def migrate(context: CommandContext):
        Project.migrate(context)

    @staticmethod
    @settings()
    def load_fixtures(context: CommandContext):
        Project.load_fixtures(context)

    @staticmethod
    @settings(only_local=True)
    def upload_sshkey(context: CommandContext):
        """
        Upload SSH key to server.
        """
        Project.upload_key(context)

    @staticmethod
    @settings(allow_sudo=True)
    def setup_ssl(context: CommandContext, artifact=None):
        if artifact:

            if not context.config.https:
                is_agree = input(
                    'We will change the value of [https] in your config file, Are you agree? Y/n: '
                ) or 'n'

                if is_agree.upper() == "Y":
                    update_config_file(key="https", value=True)

            if artifact == 'renew':
                Server.renew_ssl(context)

            elif artifact == WebServer.NGINX.value:
                Server.nginx(context)

            else:
                click.echo(click.style('[{0}] doesn\'t implemented'.format(artifact), fg='red'))
        else:
            Server.certbot(context)
            Server.letsencrypt(context)

    @staticmethod
    @settings(allow_sudo=True)
    def server_language(context: CommandContext):
        if context.connection.run('echo $LANG').ok:
            context.connection.sudo('echo "LANG=C.UTF-8" >> /etc/environment')

        if context.connection.run('echo $LC_CTYPE').ok:
            context.connection.sudo('echo "LC_CTYPE=C.UTF-8" >> /etc/environment')

        if context.connection.run('echo $LC_ALL').ok:
            context.connection.sudo('echo "LC_ALL=C.UTF-8" >> /etc/environment')

    @staticmethod
    @settings(allow_sudo=True)
    def reset_db(context: CommandContext):
        Server.reset_db(context)

    # @classmethod
    # def make_backup(cls):
    #     Global.set_user(superuser=True)
    #     with settings(hide('warnings'), warn_only=True):
    #         execute(Project.backup, hosts=env.hosts)
    #         execute(Project.download_backup, hosts=env.hosts)
    #
